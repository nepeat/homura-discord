# coding=utf-8
import logging
import os
import time
import traceback

import raven

import aiohttp
import asyncio
import asyncio_redis
import discord
from homura.lib.redis_mods import BotEncoder, UncheckedRedisProtocol
from homura.lib.stats import CustomInfluxDBClient
from homura.lib.structure import Message
from homura.lib.util import Dummy
from homura.plugins.manager import PluginManager
from typing import Optional

OPUS_LIBS = ['opus', 'libopus.so.0']

# Logging configuration
if "DEBUG_FLOOD" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.DEBUG)

if "DEBUG" in os.environ:
    logging.getLogger("homura").setLevel(level=logging.DEBUG)

log = logging.getLogger(__name__)


# Load opus libraries if not loaded already

if not discord.opus.is_loaded():
    for lib in OPUS_LIBS:
        try:
            discord.opus.load_opus(lib)
            break
        except OSError:
            pass

    if not discord.opus.is_loaded():
        raise Exception("Opus library could not be loaded.")


class NepeatBot(discord.Client):
    def __init__(self):
        self.plugins = PluginManager(self)
        self.all_permissions = set()

        self.sentry = raven.Client(
            dsn=os.environ.get("SENTRY_DSN", None),
            install_logging_hook=True
        )

        if "INFLUX_HOST" in os.environ:
            self.stats = CustomInfluxDBClient(
                host=os.environ.get("INFLUX_HOST"),
                port=int(os.environ.get("INFLUX_PORT", 8086)),
                database=os.environ.get("INFLUX__DATABASE", "homura"),
            )
        else:
            self.stats = Dummy()

        super().__init__()

        self.aiosession = aiohttp.ClientSession(loop=self.loop)

    async def create_redis(self):
        if hasattr(self, "redis"):
            return

        self.redis = await asyncio_redis.Pool.create(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 0)),
            loop=self.loop,
            poolsize=5,
            encoder=BotEncoder(),
            protocol_class=UncheckedRedisProtocol
        )

    async def real_init(self):
        await self.create_redis()
        self.plugins.load_all()

    async def _plugin_run_event(self, method, *args, **kwargs):
        start = time.time()

        try:
            await method(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                self.on_error(method.__name__, *args, **kwargs)
            except asyncio.CancelledError:
                pass

        delta = time.time() - start

        if delta > 1.0:
            self.stats.count(
                "event_timings",
                event=str(method.__name__),
                module=str(type(method.__self__).__name__),  # god why
                count=float(delta)
            )

    async def plugin_dispatch(self, event, *args, **kwargs):
        method = "on_" + event

        for plugin in self.plugins:
            func = getattr(plugin, method)

            if event == "message":
                func = getattr(plugin, "_on_message")

            asyncio.ensure_future(self._plugin_run_event(func, *args, **kwargs), loop=self.loop)

    async def send_message_object(
        self,
        message: Message,
        channel: discord.abc.Messageable,
        author: Optional[discord.User]=None,
        invoking: Optional[discord.abc.Messageable]=None
    ):
        content = message.content
        if message.reply and author:
            if content:
                content = '{}, {}'.format(author.mention, content)
            else:
                content = '{}'.format(author.mention)

        sentmsg = await channel.send(
            content,
            embed=message.embed,
            file=message.file
        )

        if message.delete_invoking and invoking:
            await asyncio.sleep(message.delete_invoking)
            await self.delete_message(invoking)

        if message.delete_after:
            await asyncio.sleep(message.delete_after)
            await self.delete_message(sentmsg)

    # Overloads

    async def delete_message(self, message):
        await self.redis.sadd("ignored:{}".format(message.guild.id), [message.id])
        await self.redis.expire("ignored:{}".format(message.guild.id), 120)

        return await message.delete()

    async def delete_messages(self, messages):
        last_guild = messages[0].guild.id
        for m in messages:
            if last_guild != m.guild.id:
                raise Exception("Mismatching guild id given for delete_messages")

        await self.redis.sadd("ignored:{}".format(messages[0].guild.id), [m.id for m in messages])
        await self.redis.expire("ignored:{}".format(messages[0].guild.id), 120)

        return await messages[0].channel.delete_messages(messages)

    async def close(self):
        await self.plugin_dispatch("logout")
        return await super().close()

    # Events

    def on_error(self, event_method, *args, **kwargs):
        self.stats.count("error", method=event_method)
        log.error("Exception in %s", event_method)
        log.error(traceback.format_exc())
        return self.sentry.captureException()

    async def on_ready(self):
        self.stats.count("ready")
        log.info("Bot ready!")

        await self.real_init()

        if hasattr(self, "shard_id") and self.shard_id:
            msg = "Shard {}/{} restarted".format(
                self.shard_id,
                self.shard_count
            )
        else:
            msg = "Bot restarted!"

        log.info(msg)
        log.info("Server count: {}".format(len(self.guilds)))

        await self.plugin_dispatch("ready")

    async def on_guild_join(self, guild):
        await self.plugin_dispatch("guild_join", guild)

    async def on_message(self, message):
        # Why. http://i.imgur.com/iQSuVnV.png
        if message.author.id == self.user.id:
            return

        self.stats.count("message", type="receive")

        if message.content == "!shard?":
            if hasattr(self, 'shard_id'):
                await message.channel.send(
                    "shard {}/{}".format(self.shard_id + 1, self.shard_count)
                )

        await self.plugin_dispatch("message", message)

    async def on_message_edit(self, before, after):
        if isinstance(before.channel, discord.abc.PrivateChannel):
            return

        # Ignore self edits.
        if before.author == self.user:
            return

        # Check: This is not a bot user.
        if before.author.bot:
            return

        await self.plugin_dispatch("message_edit", before, after)

    async def on_message_delete(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return

        # Check: Ignore self deletes.
        if message.author == self.user:
            return

        # Check: Ignore messages that we have deleted.
        if await self.redis.sismember("ignored:{}".format(message.guild.id), message.id):
            return

        # Check: Webhooks have no display name.
        if not message.author.display_name:
            return

        # Check: This is not a bot user.
        if message.author.bot:
            return

        await self.plugin_dispatch("message_delete", message)

    async def on_guild_channel_create(self, channel):
        await self.plugin_dispatch("guild_channel_create", channel)

    async def on_guild_channel_update(self, before, after):
        await self.plugin_dispatch("guild_channel_update", before, after)

    async def on_guild_channel_delete(self, channel):
        await self.plugin_dispatch("guild_channel_delete", channel)

    async def on_member_join(self, member):
        await self.plugin_dispatch("member_join", member)

    async def on_member_remove(self, member):
        await self.plugin_dispatch("member_remove", member)

    async def on_member_update(self, before, after):
        await self.plugin_dispatch("member_update", before, after)

    async def on_guild_update(self, before, after):
        await self.plugin_dispatch("guild_update", before, after)

    async def on_guild_role_create(self, role):
        await self.plugin_dispatch("guild_role_create", role)

    async def on_guild_role_delete(self, role):
        await self.plugin_dispatch("guild_role_delete", role)

    async def on_guild_role_update(self, before, after):
        await self.plugin_dispatch("guild_role_update", before, after)

    async def on_voice_state_update(self, member, before, after):
        await self.plugin_dispatch("voice_state_update", member, before, after)

    async def on_member_ban(self, guild, member):
        await self.plugin_dispatch("member_ban", guild, member)

    async def on_member_unban(self, guild, member):
        await self.plugin_dispatch("member_unban", guild, member)

    async def on_typing(self, channel, user, when):
        if isinstance(channel, discord.abc.PrivateChannel):
            return

        await self.plugin_dispatch("typing", channel, user, when)

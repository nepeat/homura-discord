# coding=utf-8
import asyncio
import logging
import os
import random
import signal
import time
import traceback
from typing import Optional

import aiohttp
import asyncio_redis
import discord
import raven

from homura.lib.stats import CustomInfluxDBClient
from homura.lib.structure import Message
from homura.plugins.manager import PluginManager
from homura.util import Dummy

OPUS_LIBS = ['opus', 'libopus.so.0']

# Logging configuration

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.DEBUG)

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
        self.plugins = []
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

        self.loop.create_task(self.create_redis())
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

        # Exit signal handlers
        for signame in ('SIGINT', 'SIGTERM'):
            self.loop.add_signal_handler(getattr(signal, signame), self.signal)

    async def create_redis(self):
        self.redis = await asyncio_redis.Pool.create(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 0)),
            loop=self.loop,
            poolsize=5
        )

    async def _plugin_run_event(self, method, *args, **kwargs):
        start = time.time()

        try:
            await method(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(method.__name__, *args, **kwargs)
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
        channel: discord.Channel,
        author: Optional[discord.User]=None,
        invoking: Optional[discord.Message]=None
    ):
        content = message.content
        if message.reply and author:
            if content:
                content = '{}, {}'.format(author.mention, content)
            else:
                content = '{}'.format(author.mention)

        sentmsg = await self.send_message(
            channel,
            content,
            embed=message.embed
        )

        if message.delete_invoking and invoking:
            await asyncio.sleep(message.delete_invoking)
            await self.delete_message(invoking)

        if message.delete_after:
            await asyncio.sleep(message.delete_after)
            await self.delete_message(sentmsg)

    def signal(self):
        self.loop.create_task(self.logout())

    # Overloads

    async def send_message(self, *args, **kwargs):
        self.stats.count("message", type="send")
        return await super().send_message(*args, **kwargs)

    async def delete_message(self, message):
        await self.redis.sadd("ignored:{}".format(message.server.id), [message.id])
        await self.redis.expire("ignored:{}".format(message.server.id), 120)

        return await super().delete_message(message)

    async def delete_messages(self, messages):
        await self.redis.sadd("ignored:{}".format(messages[0].server.id), [m.id for m in messages])
        await self.redis.expire("ignored:{}".format(messages[0].server.id), 120)

        return await super().delete_messages(messages)

    async def logout(self):
        await self.plugin_dispatch("logout")
        return await super().logout()

    # Events

    async def on_error(self, event_method, *args, **kwargs):
        self.stats.count("error", method=event_method)
        log.error("Exception in %s", event_method)
        log.error(traceback.format_exc())
        return self.sentry.captureException()

    async def on_ready(self):
        self.stats.count("ready")
        log.info("Bot ready!")

        if hasattr(self, "shard_id") and self.shard_id:
            msg = "Shard {}/{} restarted".format(
                self.shard_id,
                self.shard_count
            )
        else:
            msg = "Bot restarted!"

        log.info(msg)
        log.info("Server count: {}".format(len(self.servers)))

        await self.plugin_dispatch("ready")

    async def on_server_join(self, server):
        await self.plugin_dispatch("server_join", server)

    async def on_message(self, message):
        # Why. http://i.imgur.com/iQSuVnV.png
        if message.author.id == self.user.id:
            return

        self.stats.count("message", type="receive")

        if message.content == "!shard?":
            if hasattr(self, 'shard_id'):
                await self.send_message(
                    message.channel,
                    "shard {}/{}".format(self.shard_id + 1, self.shard_count)
                )

        await self.plugin_dispatch("message", message)

    async def on_message_edit(self, before, after):
        if before.channel.is_private:
            return

        await self.plugin_dispatch("message_edit", before, after)

    async def on_message_delete(self, message):
        if message.channel.is_private:
            return

        await self.plugin_dispatch("message_delete", message)

    async def on_channel_create(self, channel):
        if channel.is_private:
            return

        await self.plugin_dispatch("channel_create", channel)

    async def on_channel_update(self, before, after):
        if before.is_private:
            return

        await self.plugin_dispatch("channel_update", before, after)

    async def on_channel_delete(self, channel):
        if channel.is_private:
            return

        await self.plugin_dispatch("channel_delete", channel)

    async def on_member_join(self, member):
        await self.plugin_dispatch("member_join", member)

    async def on_member_remove(self, member):
        await self.plugin_dispatch("member_remove", member)

    async def on_member_update(self, before, after):
        await self.plugin_dispatch("member_update", before, after)

    async def on_server_update(self, before, after):
        await self.plugin_dispatch("server_update", before, after)

    async def on_server_role_create(self, role):
        await self.plugin_dispatch("server_role_create", role)

    async def on_server_role_delete(self, role):
        await self.plugin_dispatch("server_role_delete", role)

    async def on_server_role_update(self, before, after):
        await self.plugin_dispatch("server_role_update", before, after)

    async def on_voice_state_update(self, before, after):
        await self.plugin_dispatch("voice_state_update", before, after)

    async def on_member_ban(self, member):
        await self.plugin_dispatch("member_ban", member)

    async def on_member_unban(self, server, member):
        await self.plugin_dispatch("member_unban", server, member)

    async def on_typing(self, channel, user, when):
        if channel.is_private:
            return

        await self.plugin_dispatch("typing", channel, user, when)

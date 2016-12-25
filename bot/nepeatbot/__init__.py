import asyncio
import logging
import os
import traceback

from typing import List

import aiohttp
import asyncio_redis
import discord
import raven
import statsd

from nepeatbot.plugins.common import Message
from nepeatbot.plugins.manager import PluginManager
from nepeatbot.util import Dummy

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.DEBUG)

log = logging.getLogger(__name__)


class NepeatBot(discord.Client):
    def __init__(self):
        self.sentry = raven.Client(
            dsn=os.environ.get("SENTRY_DSN", None),
            install_logging_hook=True
        )

        if "STATSD_HOST" in os.environ:
            self.stats = statsd.StatsClient(os.environ.get("STATSD_HOST"), os.environ.get("STATSD_PORT", 8125))
        else:
            self.stats = Dummy()

        super().__init__()

        self.loop.create_task(self.create_redis())
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

    async def create_redis(self):
        self.redis = await asyncio_redis.Pool.create(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 0)),
            loop=self.loop,
            poolsize=5
        )

    async def _plugin_run_event(self, method, *args, **kwargs):
        try:
            await method(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(method.__name__, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    async def plugin_dispatch(self, event, *args, **kwargs):
        method = "on_" + event
        server = None
        plugins = {plugin for plugin in self.plugins if plugin.is_global}

        for arg in args:
            if hasattr(arg, "server"):
                server = arg.server
                break

        if server:
            plugins |= set(await self.get_plugins(server))

        for plugin in plugins:
            func = getattr(plugin, method)

            if event == "message":
                func = getattr(plugin, "_on_message")

            if hasattr(self, method):
                asyncio.ensure_future(self._plugin_run_event(func, *args, **kwargs), loop=self.loop)

    async def send_message_object(self, message: Message, author: discord.User=None):
        content = message.content
        if message.reply and author:
            content = '{}, {}'.format(author.mention, content)

        sentmsg = await self.send_message(
            message.channel,
            content,
            embed=message.embed
        )

        if message.delete_after:
            await asyncio.sleep(message.delete_after)
            await self.delete_message(sentmsg)

        if message.delete_invoking:
            await asyncio.sleep(5)
            self.delete_message(message)

    # Events
    async def get_plugins(self, server):
        plugins = await self.plugin_manager.get_all(server)
        return plugins

    async def send_message(self, *args, **kwargs):
        self.stats.incr("nepeatbot.message,type=send")
        return await super().send_message(*args, **kwargs)

    async def on_error(self, event_method, *args, **kwargs):
        self.stats.incr("nepeatbot.error")
        log.error("Exception in %s", event_method)
        log.error(traceback.format_exc())
        self.sentry.captureException()

    async def on_ready(self):
        self.stats.incr("nepeatbot.ready")
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

        self.stats.incr("nepeatbot.message,type=receive", rate=0.1)
        if message.channel.is_private:
            return

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

    async def on_member_unban(self, member):
        await self.plugin_dispatch("member_unban", member)

    async def on_typing(self, channel, user, when):
        if channel.is_private:
            return

        await self.plugin_dispatch("typing", channel, user, when)

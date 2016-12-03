import logging
import os
import aiohttp
import raven
import discord
import asyncio_redis

from influxdb import InfluxDBClient

from nepeatbot.plugins.manager import PluginManager

# Logging

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

        self.influxdb = InfluxDBClient.from_DSN(os.environ.get("INFLUXDB_DSN", None))
        if self.influxdb.database not in [x["name"] for x in self.influxdb.get_list_database()]:
            self.influxdb.create_database(self.influxdb.database)

        super().__init__()
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

    @property
    async def redis(self):
        if not hasattr(self, "redis"):
            self.redis = await asyncio_redis.Pool.create(
                host=os.environ.get("REDIS_HOST", "localhost"),
                port=int(os.environ.get("REDIS_PORT", 6379)),
                db=int(os.environ.get("REDIS_DB", 0)),
                loop=self.loop,
                poolsize=5
            )
        else:
            return self.redis

    # Events
    async def get_plugins(self, server):
        plugins = await self.plugin_manager.get_all(server)
        return plugins

    async def on_ready(self):
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
        for server in self.servers:
            log.info(server.name)

        for plugin in self.plugins:
            self.loop.create_task(plugin.on_ready())

    async def on_server_join(self, server):
        for plugin in self.plugins:
            if plugin.is_global:
                self.loop.create_task(plugin.on_server_join(server))

    async def on_message(self, message):
        if message.channel.is_private:
            return

        server = message.server

        if message.content == "!shard?":
            if hasattr(self, 'shard_id'):
                await self.send_message(
                    message.channel,
                    "shard {}/{}".format(self.shard_id + 1, self.shard_count)
                )

        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin._on_message(message))

    async def on_message_edit(self, before, after):
        if before.channel.is_private:
            return

        server = after.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_message_edit(before, after))

    async def on_message_delete(self, message):
        if message.channel.is_private:
            return

        server = message.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_message_delete(message))

    async def on_channel_create(self, channel):
        if channel.is_private:
            return

        server = channel.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_channel_create(channel))

    async def on_channel_update(self, before, after):
        if before.is_private:
            return

        server = after.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_channel_update(before, after))

    async def on_channel_delete(self, channel):
        if channel.is_private:
            return

        server = channel.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_channel_delete(channel))

    async def on_member_join(self, member):
        server = member.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_member_join(member))

    async def on_member_remove(self, member):
        server = member.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_member_remove(member))

    async def on_member_update(self, before, after):
        server = after.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_member_update(before, after))

    async def on_server_update(self, before, after):
        server = after
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_server_update(before, after))

    async def on_server_role_create(self, role):
        server = role.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_server_role_create(role))

    async def on_server_role_delete(self, role):
        server = role.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_server_role_delete(role))

    async def on_server_role_update(self, before, after):
        server = None
        for s in self.servers:
            if after.id in map(lambda r: r.id, s.roles):
                server = s
                break

        if server is None:
            return

        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_server_role_update(before, after))

    async def on_voice_state_update(self, before, after):
        if after is None and before is None:
            return
        elif after is None:
            server = before.server
        elif before is None:
            server = after.server
        else:
            server = after.server

        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_voice_state_update(before, after))

    async def on_member_ban(self, member):
        server = member.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_member_ban(member))

    async def on_member_unban(self, member):
        server = member.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_member_unban(member))

    async def on_typing(self, channel, user, when):
        if channel.is_private:
            return

        server = channel.server
        enabled_plugins = await self.get_plugins(server)
        for plugin in enabled_plugins:
            self.loop.create_task(plugin.on_typing(channel, user, when))

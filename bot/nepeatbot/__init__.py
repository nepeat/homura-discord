import logging
import os
import json

import aiohttp
import asyncio
import raven
import discord
import redis
from nepeatbot.model.connections import redis_pool
from nepeatbot.model.validators import url_regex, validate_url
from itertools import zip_longest

# Logging
logging.basicConfig(level=logging.INFO)

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

class NepeatBot(discord.Client):
    def __init__(self):
        self.sentry = raven.Client(dsn=os.environ.get("SENTRY_DSN", None))

        super().__init__()
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.bot_url = os.environ.get("BOT_WEB", "http://localhost:5000")

    @property
    def redis(self):
        return redis.StrictRedis(
            connection_pool=redis_pool,
            decode_responses=True,
        )

    async def handle_quote(self, message):
        content = message.content.lower()
        urls = url_regex.search(content)

        if message.attachments:
            return
        elif urls:
            for url in urls.groups():
                if not await validate_url(self.aiosession, url):
                    return await self.delete_message(message)
        else:
            await self.delete_message(message)

    async def handle_command(self, message):
        _command = message.content.strip().split("!", 2)[1]

        command, *args = _command.split()

        if command == "mute":
            for user in message.mentions:
                self.redis.sadd("mod:muted", user.id)
        elif command == "unmute":
            for user in message.mentions:
                self.redis.srem("mod:muted", user.id)
        elif command == "purge":
            purged = [x.id for x in message.mentions]

            if not purged:
                log.error("no purged")

            for channel in message.server.channels:
                removed = []
                if str(channel.type) != "text":
                    continue

                async for msg in self.logs_from(channel, limit=200):
                    if msg.author.id in purged:
                        removed.append(msg)

                if not removed:
                    continue

                for messages in zip_longest(*(iter(removed),) * 100):
                    messages = [message for message in messages if message]
                    await self.delete_messages(messages)
        elif command == "purgechan":
            removed = []
            async for msg in self.logs_from(message.channel, limit=200):
                removed.append(msg)

            for messages in zip_longest(*(iter(removed),) * 100):
                messages = [message for message in messages if message]
                await self.delete_messages(messages)
        elif command == "remove":
            message = await self.get_message(message.channel, args[0])
            await self.delete_message(message)
        elif command == "undelete":
            messages = self.redis.lrange("deleted:" + message.channel.id, -5, -1)
            if not messages:
                return await self.send_message(message.channel, "None")

            try:
                messages = [json.loads(_) for _ in messages]
            except:
                pass

            output = "\n".join(["__{sender}__ - {message}".format(
                sender=deleted["sender"],
                message=deleted["message"]["clean"]
            ) for deleted in messages])

            await self.send_message(message.channel, output)
        elif command == "metaserver":
            self.redis.sadd("allowdeleted", message.server.id)
        elif command == "metaon":
            self.redis.sadd("allowdeleted", message.channel.id)
        elif command == "metaoff":
            self.redis.srem("allowdeleted", message.channel.id)

            if "server" in args:
                self.redis.srem("allowdeleted", message.server.id)

    async def log(self, message: str):
        log_channel = self.get_channel("204802833504010240")
        await self.send_message(log_channel, message)

    async def log_member(self, member, joining):
        action = "join" if joining else "leave"

        await self.push_event(action, member.server, None, {
            "name": member.name
        })

    # Events
    async def on_member_join(self, member):
        await self.log_member(member, True)

    async def on_member_remove(self, member):
        await self.log_member(member, False)

    async def on_member_update(self, before, after):
        if not self.valid_server(before.server):
            return

        if before.nick != after.nick:
            await self.log(":pencil: `{old}` is now known as `{new}` on **{server}**".format(
                old=before.nick if before.nick else before.name,
                new=after.nick if after.nick else after.name,
                server=before.server.name
            ))

    async def on_voice_state_update(self, before, after):
        if not self.redis.exists("voicefuck"):
            return

        if after.id in (
            "66153853824802816",
            "173749502300258304",
            "139053549911932929",
            "139168649880535040",
            "126916532428079104",
        ) and (after.voice.deaf or after.voice.mute):
            await self.server_voice_state(after, mute=False, deafen=False)

    def valid_server(self, server):
        if server.id in (
            "138747544162402305",  # Mainland
            "204797909361885184"   # H E L L
        ):
            return True

        return False

    async def on_message(self, message):
        if not self.valid_server(message.server):
            return

        # Ignore self messages.
        if message.author == self.user:
            return

        # racist
        if self.redis.sismember("mod:muted", message.author.id):
            try:
                await self.delete_message(message)
            except discord.errors.Forbidden:
                log.error("gg no perms")

        message_content = message.content.strip()
        lower_content = message_content.lower()

        if message.channel.id == "195245746612731904":
            await self.handle_quote(message)
        elif lower_content.startswith("!") and message.author.id == "66153853824802816":
            await self.handle_command(message)

    async def on_message_edit(self, before, after):
        # Ignore self messages.
        if before.author == self.user:
            return

        if before.content == after.content:
            return

        await self.push_event("edit", before.server, before.channel, {
            "sender": {
                "id": before.author.id,
                "display_name": before.author.display_name,
            },
            "edit": {
                "before": before.content,
                "after": after.content,
            }
        })

    async def on_message_delete(self, message):
        if not self.valid_server(message.server):
            return

        if message.author == self.user:
            return

        await self.push_event("delete", message.server, message.channel, {
            "sender": {
                "id": message.author.id,
                "display_name": message.author.display_name,
            },
            "message": message.content
        })

    async def push_event(self, event_type, server, channel, data):
        payload = {
            "type": event_type,
            "server": server.id,
            "channel": channel.id,
            "data": data
        }

        with aiohttp.Timeout(5):
            try:
                async with self.aiosession.post(
                    url=self.bot_url + "/push/event",
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    reply = await response.json()
                    if reply["status"] == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
            except aiohttp.errors.ClientError:
                return False

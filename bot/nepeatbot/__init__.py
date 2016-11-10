import logging
import os
import json
import traceback
import aiohttp
import asyncio
import raven
import discord
import redis
from nepeatbot.model.connections import redis_pool
from nepeatbot.model.validators import url_regex, validate_url
from itertools import zip_longest

# Logging

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

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

        if command == "purge":
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
            messages = await self.get_events("delete", message.server, message.channel)
            if not messages:
                return await self.send_message(message.channel, "None")

            output = "\n".join(["__{sender}__ - {message}".format(
                sender=deleted["sender"]["display_name"],
                message=deleted["message"]
            ) for deleted in messages])

            await self.send_message(message.channel, output)
        elif command == "metaon":
            self.redis.sadd("allowdeleted", message.channel.id)
        elif command == "metaoff":
            self.redis.srem("allowdeleted", message.channel.id)

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
        old = before.nick if before.nick else before.name
        new = after.nick if after.nick else after.name

        if old == new:
            return

        await self.push_event("rename", before.server, None, {
            "old": old,
            "new": new
        })

    async def on_channel_update(self, before, after):
        if before.topic != after.topic:
            await self.push_event("topic", before.server, before.channel, {
                "topic": {
                    "before": before.topic,
                    "after": after.topic,
                }
            })

        if before.name != after.name:
            await self.push_event("rename_channel", before.server, before.channel, {
                "channel": {
                    "before": before.name,
                    "after": after.name,
                }
            })

    async def on_server_update(self, before, after):
        if before.name != after.name:
            await self.push_event("rename_server", before.server, before.channel, {
                "server": {
                    "before": before.name,
                    "after": after.name,
                }
            })

    async def on_message(self, message):
        # Ignore self messages.
        if message.author == self.user:
            return

        message_content = message.content.strip()
        lower_content = message_content.lower()

        if message.channel.id == "195245746612731904":  # XXX quote-only legacy
            await self.handle_quote(message)
        elif lower_content.startswith("!") and message.author.id == "66153853824802816":
            try:
                await self.handle_command(message)
            except Exception:
                traceback.print_exc()
                self.sentry.captureException()

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
                "before": before.clean_content,
                "after": after.clean_content,
            }
        })

    async def on_message_delete(self, message):
        if message.author == self.user:
            return

        await self.push_event("delete", message.server, message.channel, {
            "sender": {
                "id": message.author.id,
                "display_name": message.author.display_name,
            },
            "message": message.clean_content
        })

    async def push_event(self, event_type, server, channel=None, data=None):
        payload = {
            "type": event_type,
            "server": server.id,
            "channel": channel.id if channel else None,
            "data": data if data else {}
        }

        try:
            async with self.aiosession.post(
                url=self.bot_url + "/events/push",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("status") == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
        except aiohttp.errors.ClientError:
            return False

    async def get_events(self, event_type, server, channel=None):
        params = {
            "server": server.id,
        }

        if channel:
            params.update({"channel": channel.id})

        try:
            async with self.aiosession.get(
                url=self.bot_url + "/events/" + event_type,
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("status") == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
                        return None
                    return reply.get("events", None)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    pass
        except aiohttp.errors.ClientError:
            pass

        return None

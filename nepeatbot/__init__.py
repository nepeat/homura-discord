import logging
import os

import asyncio
import discord
import redis
from nepeatbot.model.connections import redis_pool

# Logging
logging.basicConfig(level=logging.INFO)

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

class NepeatBot(discord.Client):
    def __init__(self):
        super().__init__()

    @property
    def redis(self):
        return redis.StrictRedis(
            connection_pool=redis_pool,
            decode_responses=True,
        )

    async def handle_quote(self, message):
        content = message.content.lower()

        if message.attachments or "http" in content:
            return

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
            messages = []
            purged = [x.id for x in message.mentions]

            if not purged:
                log.error("no purged")

            for channel in message.server.channels:
                if str(channel.type) != "text":
                    continue

                async for msg in self.logs_from(channel, limit=200):
                    if msg.author.id in purged:
                        messages.append(msg)

            for message in messages:
                log.info("Purging message '%s'", message.content.strip())
                await self.delete_message(message)
                await asyncio.sleep(0.20)

    async def log(self, message: str):
        log_channel = self.get_channel("196024839562067970")
        await self.send_message(log_channel, message)

    async def log_member(self, member, joining):
        message = "{emoji} **{name}** has {action} '{server}'.".format(
            emoji=":white_check_mark:" if joining else ":door:",
            name=member.name,
            action="joined" if joining else "left",
            server=member.server.name
        )

        await self.log(message)

    # Events
    async def on_member_join(self, member):
        await self.log_member(member, True)

    async def on_member_remove(self, member):
        await self.log_member(member, False)

    async def on_message(self, message):
        # Horribly hardcoded meme server ID.
        if message.server.id not in ("138747544162402305", "189250510987984897"):
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

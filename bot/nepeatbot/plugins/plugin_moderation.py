import logging

from nepeatbot.plugins.common import PluginBase, command, Message
from itertools import zip_longest

log = logging.getLogger(__name__)

class ModerationPlugin(PluginBase):
    is_global = True
    requires_admin = True

    @command("purgeuser")
    async def cmd_purge(self, message):
        mentions = [x.id for x in message.mentions]

        if not mentions:
            return Message("User mention is missing!")

        deleted = 0

        for channel in message.server.channels:
            removed = []
            if str(channel.type) != "text":
                continue

            async for msg in self.bot.logs_from(channel, limit=200):
                if msg.author.id in mentions:
                    removed.append(msg)

            if not removed:
                continue

            deleted = deleted + len(removed)

            if len(removed) == 1:
                await self.bot.delete_message(removed[0])
                continue

            for messages in zip_longest(*(iter(removed),) * 100):
                messages = [message for message in messages if message]
                await self.redis.sadd("ignored:{}".format(message.server.id), [m.id for m in messages])
                await self.bot.delete_messages(messages)

            await self.redis.expire("ignored:{}".format(message.server.id), 120)

        return Message("{} messages removed!".format(deleted))

    @command(patterns=[
        "purgechan (\d+)",
        "purgechan"
    ])
    async def cmd_purge_chan(self, message, args):
        try:
            limit = int(args[0])

            if limit > 600 or limit < 0:
                raise ValueError()
        except (TypeError, ValueError):
            limit = 100

        removed = []
        async for msg in self.bot.logs_from(message.channel, limit=limit):
            removed.append(msg)

        for messages in zip_longest(*(iter(removed),) * 100):
            messages = [message for message in messages if message]
            await self.bot.delete_messages(messages)
            await self.redis.sadd("ignored:{}".format(message.server.id), [m.id for m in messages])

        await self.redis.expire("ignored:{}".format(message.server.id), 120)

        return Message("{} messages removed!".format(len(removed)))

    @command("remove (\d+)")
    async def cmd_remove(self, message, args):
        message = await self.bot.get_message(message.channel, args[0])
        if message:
            await self.redis.sadd("ignored:{}".format(message.server.id), [message.id])
            await self.bot.delete_message(message)


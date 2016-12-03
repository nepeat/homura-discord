import logging

from nepeatbot.plugins.common import PluginBase, command
from itertools import zip_longest

log = logging.getLogger(__name__)

class ModerationPlugin(PluginBase):
    is_global = True
    requires_admin = True

    @command("purge")
    async def cmd_purge(self, message, args):
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

    @command("purgechan (\d+)")
    async def cmd_purge_chan(self, message, args):
        try:
            limit = int(args[0])

            if limit > 600 or limit < 0:
                raise ValueError()
        except (TypeError, ValueError):
            limit = 100

        removed = []
        async for msg in self.logs_from(message.channel, limit=limit):
            removed.append(msg)

        for messages in zip_longest(*(iter(removed),) * 100):
            messages = [message for message in messages if message]
            await self.delete_messages(messages)

    @command("remove")
    async def cmd_remove(self, message, message_id):
        message = await self.get_message(message.channel, message_id)
        await self.delete_message(message)

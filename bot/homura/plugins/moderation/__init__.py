# coding=utf-8
import logging
from itertools import zip_longest

from homura.lib.structure import Message, CommandError
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class ModerationPlugin(PluginBase):
    requires_admin = True

    @command(
        "purgeuser",
        permission_name="mod.purge.user",
        description="Purges a user's messages from all channels.",
        usage="purgeuser <@mentions>"
    )
    async def cmd_purge(self, message):
        mentions = [x.id for x in message.mentions]

        if not mentions:
            return Message("User mention is missing!")

        deleted = 0

        for channel in message.guild.channels:
            removed = []
            if str(channel.type) != "text":
                continue

            async for msg in channel.history(limit=200):
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
                await self.bot.delete_messages(messages)

        return Message("{} messages removed!".format(deleted))

    @command(
        patterns=[
            "purgechan (\d+)",
            "purgechan"
        ],
        permission_name="mod.purge.channel",
        description="Purges a channel up to 1000 messages (100 purged by default).",
        usage="purgechan <optional:200>"
    )
    async def cmd_purge_chan(self, message, args):
        try:
            limit = int(args[0])

            if limit > 1000 or limit < 0:
                raise ValueError()
        except (TypeError, ValueError):
            limit = 100

        removed = []
        async for msg in message.channel.history(limit=limit):
            removed.append(msg)

        for messages in zip_longest(*(iter(removed),) * 100):
            messages = [message for message in messages if message]
            await self.bot.delete_messages(messages)

        return Message("{} messages removed!".format(len(removed)))

    @command(
        "remove (\d+)",
        permission_name="mod.remove",
        description="Removes a message by message ID.",
        usage="remove <message id>"
    )
    async def cmd_remove(self, message, args):
        message_to_delete = await message.channel.get_message(args[0])
        if message_to_delete:
            await self.bot.delete_message(message_to_delete)
        await self.bot.delete_message(message)

    @command(
        patterns=[
            r"autorole (.+)",
            r"autorole"
        ],
        permission_name="mod.autorole",
        description="Toggles a role that will be automatically given to new members.",
        usage="autorole <role_name>",
    )
    async def cmd_autorole(self, guild, args):
        role = self.get_role(guild, args[0])

        if not role:
            raise CommandError("Role does not exist.")

        role_exists = await self.redis.sismember(f"server:%s:autoroles" % (guild.id), role.id)
        action = self.redis.srem if role_exists else self.redis.sadd
        await action("server:%s:autoroles" % (guild.id), [role.id])

        return Message(f"Role has been {'removed' if role_exists else 'added'}!")

    async def on_member_join(self, member):
        roles = await self.redis.smembers_asset("server:%s:autoroles" % (member.guild.id))

        for role_id in roles:
            role = self.get_role(member.guild, role_id)
            if not role:
                continue

            await member.add_roles(role)

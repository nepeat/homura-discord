# coding=utf-8
import logging
from itertools import zip_longest

import discord

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class RolesPlugin(PluginBase):
    @command(
        patterns=[
            r"autorole (.+)",
            r"autorole"
        ],
        permission_name="mod.autorole",
        description="Toggles a role that will be automatically given to new members.",
        usage="autorole <role_name>",
    )
    async def cmd_autorole(self, message, server, args):
        role = self.get_role(server, args[0])

        if not role:
            return Message("Role does not exist.")

        role_exists = await self.redis.sismember("server:%s:autoroles" % (server.id), role.id)
        action = self.redis.srem if role_exists else self.redis.sadd
        await action("server:%s:autoroles" % (server.id), [role.id])

        return Message(f"Role has been {'removed' if role_exists else 'added'}!")

    async def on_member_join(self, member):
        roles = await self.redis.smembers_asset("server:%s:autoroles" % (member.server.id))

        for role_id in roles:
            role = self.get_role(member.server, role_id)
            if not role:
                continue

            await self.bot.add_roles(member, role)

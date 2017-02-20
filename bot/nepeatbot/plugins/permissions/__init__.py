import datetime
import logging
import xml.etree.ElementTree as ET

import aiohttp
import discord

from nepeatbot.plugins.common import Message, PluginBase, command
from nepeatbot.util import sanitize

log = logging.getLogger(__name__)


class PermissionsPlugin(PluginBase):
    @command("permission list (server|channel)", permission_name="permissions.list")
    async def list_permission(self, permissions, args):
        perm_list = await permissions.get_perms("server" in args[0].lower())
        output = "__**Permissions**__\n"
        output += "\n".join(perm_list)
        return Message(output)

    @command("permission channel add (.+)", permission_name="permissions.add.channel")
    async def channel_add_permission(self, permissions, args):
        await permissions.add(args[0])
        return Message(
            f"`{sanitize(args[0])}` has been added!"
        )

    @command("permission channel remove (.+)", permission_name="permissions.remove.channel")
    async def channel_remove_permission(self, permissions, args):
        await permissions.remove(args[0])
        return Message(
            f"`{sanitize(args[0])}` has been removed!"
        )

    @command("permission server add (.+)", permission_name="permissions.add.server")
    async def server_add_permission(self, permissions, args):
        await permissions.add(args[0], serverwide=False)
        return Message(
            f"`{sanitize(args[0])}` has been added serverwide!"
        )

    @command("permission server remove (.+)", permission_name="permissions.remove.server")
    async def server_remove_permission(self, permissions, args):
        await permissions.remove(args[0], serverwide=False)
        return Message(
            f"`{sanitize(args[0])}` has been removed serverwide!"
        )

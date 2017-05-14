# coding=utf-8
import logging

import discord
from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.util import sanitize

log = logging.getLogger(__name__)


class PermissionsPlugin(PluginBase):
    @command(
        "permission list (server|channel)",
        permission_name="permissions.list",
        description="Lists active permissions for a server or channel.",
        usage="permission list [server|channel]"
    )
    async def list_permission(self, permissions, args):
        perm_list = await permissions.get_perms("server" in args[0].lower())
        output = "__**Permissions**__\n"
        output += "\n".join(perm_list)
        return Message(output)

    @command(
        "permission channel add (.+)",
        permission_name="permissions.add.channel",
        description="Adds permissions to a channel.",
        usage="permission channel add <permission>"
    )
    async def channel_add_permission(self, permissions, args):
        await permissions.add(args[0])
        return Message(
            f"`{sanitize(args[0])}` has been added!"
        )

    @command(
        "permission channel remove (.+)",
        permission_name="permissions.remove.channel",
        description="Removes permissions from a channel.",
        usage="permission channel remove <permission>"
    )
    async def channel_remove_permission(self, permissions, args):
        await permissions.remove(args[0])
        return Message(
            f"`{sanitize(args[0])}` has been removed!"
        )

    @command(
        "permission server add (.+)",
        permission_name="permissions.add.server",
        description="Adds permissions to a server.",
        usage="permission server add <permission>"
    )
    async def server_add_permission(self, permissions, args):
        await permissions.add(args[0], serverwide=False)
        return Message(
            f"`{sanitize(args[0])}` has been added serverwide!"
        )

    @command(
        "permission server remove (.+)",
        permission_name="permissions.remove.server",
        description="Removes permissions from a server.",
        usage="permission server remove <permission>"
    )
    async def server_remove_permission(self, permissions, args):
        await permissions.remove(args[0], serverwide=False)
        return Message(
            f"`{sanitize(args[0])}` has been removed serverwide!"
        )
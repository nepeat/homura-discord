# coding=utf-8
import logging

import discord
from homura.lib.structure import Message
from homura.lib.util import sanitize
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class PermissionsPlugin(PluginBase):
    @command(
        "permission list",
        permission_name="permissions.list",
        description="Lists active permissions for a server or channel.",
        usage="permission list [server|channel]"
    )
    async def list_permission(self, permissions, guild):
        embed = discord.Embed(
            title="Permissions"
        )

        guild_perms = await permissions.get_perms(guildonly=True)
        embed.add_field(
            name="Server",
            value="\n".join(guild_perms if guild_perms else ["None!"])
        )

        for channel in guild.channels:
            channel_perms = [x for x in await permissions.get_perms(channel.id) if x not in guild_perms]
            if not channel_perms:
                continue

            embed.add_field(
                name=f"#{channel.name}",
                value="\n".join(channel_perms if channel_perms else ["None!"])
            )

        return Message(embed)

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
    async def guild_add_permission(self, permissions, args):
        await permissions.add(args[0], guildwide=True)
        return Message(
            f"`{sanitize(args[0])}` has been added serverwide!"
        )

    @command(
        "permission server remove (.+)",
        permission_name="permissions.remove.server",
        description="Removes permissions from a server.",
        usage="permission server remove <permission>"
    )
    async def guild_remove_permission(self, permissions, args):
        await permissions.remove(args[0], guildwide=True)
        return Message(
            f"`{sanitize(args[0])}` has been removed serverwide!"
        )

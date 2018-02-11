# coding=utf-8
import logging
import operator

import discord

from homura.lib.structure import CommandError, Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class GeneralPlugin(PluginBase):
    def get_all_commands(self, filter_plugin="all", owner=False) -> dict:
        filter_plugin = filter_plugin.strip().lower()
        output = {}

        for plugin in self.bot.plugins:
            if plugin.owner_only and not owner:
                continue

            plugin_name = plugin.__class__.__name__.replace("Plugin", "")
            if filter_plugin not in ("all", "permissions") and plugin_name.lower() != filter_plugin:
                continue

            if plugin_name not in output:
                output[plugin_name] = []

            for command_name, command_func in sorted(plugin.commands.items()):
                name = command_func.info["name"]
                description = command_func.info["description"]

                output[plugin_name].append({
                    "name": name,
                    "description": description,
                    "global": command_func.info.get("global", False),
                    "permission": command_func.info.get("permission")
                })

            # bad
            output[plugin_name] = sorted(output[plugin_name], key=operator.itemgetter("name"))

        return output

    @command(
        patterns=[
            "help (.+)",
            "help$"
        ],
        permission_name="general.help",
        description="Help command.",
        global_command=True,
        usage="help [section|permissions]"
    )
    async def help(self, is_owner, permissions, args):
        section = "all"

        if args:
            section = args[0]

        em = discord.Embed(title='Bot commands available to you', colour=discord.Colour.blue())

        for plugin_name, commands in self.get_all_commands(section, is_owner).items():
            listed_commands = ""

            for command in commands:
                can_use = permissions.can(command["permission"], blacklist_only=command["global"]) or is_owner

                if not can_use and section != "permissions":
                    continue

                if section == "permissions":
                    description = command["permission"]
                else:
                    description = command["description"]

                listed_commands += f"{command['name']} - {description}\n"

            if listed_commands:
                em.add_field(
                    name=plugin_name,
                    value=listed_commands
                )

        if not em.fields:
            raise CommandError(f"No commands were found for section '{section}.'")

        return Message(em)

    @command(
        "serverinfo",
        permission_name="general.info",
        description="Gets information of your server.",
        usage="serverinfo",
        global_command=True
    )
    async def serverinfo(self, guild):
        embed = discord.Embed(
            color=discord.Colour.blue(),
        )

        embed.set_author(name=f"{guild.name}", icon_url=guild.icon_url)
        embed.set_thumbnail(url=guild.icon_url)

        fields = [
            ["Owner", guild.owner.name],
            ["Members", guild.member_count],
            ["Roles", len(guild.roles)],
            ["Creation date", guild.created_at.strftime("%B %d, %Y %I:%M %p UTC")]
        ]

        for group in fields:
            embed.add_field(
                name=group[0],
                value=group[1]
            )

        embed.set_footer(text=f"ID: {guild.id}")

        return Message(embed)

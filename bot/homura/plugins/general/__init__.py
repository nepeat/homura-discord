# coding=utf-8
import datetime
import logging
import operator

import discord
from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class GeneralPlugin(PluginBase):
    def get_all_commands(self, owner=False) -> dict:
        output = {}

        for plugin in self.bot.plugins:
            if plugin.owner_only and not owner:
                continue

            plugin_name = plugin.__class__.__name__.replace("Plugin", "")
            if plugin_name not in output:
                output[plugin_name] = []

            for command_name, command_func in sorted(plugin.commands.items()):
                name = command_func.info["name"]
                description = command_func.info["description"]

                output[plugin_name].append({
                    "name": name,
                    "description": description,
                    "permission": command_func.info.get("permission")
                })

            # bad
            output[plugin_name] = sorted(output[plugin_name], key=operator.itemgetter("name"))

        return output

    @command(
        "help",
        permission_name="general.help",
        description="Help command.",
        global_command=True
    )
    async def help(self, message, is_owner):
        em = discord.Embed(title='Bot commands', colour=discord.Colour.blue())

        for plugin_name, commands in self.get_all_commands(is_owner).items():
            listed_commands = ""

            for command in commands:
                listed_commands += f"{command['name']} - {command['description']}\n"

            em.add_field(
                name=plugin_name,
                value=listed_commands
            )

        return Message(embed=em)

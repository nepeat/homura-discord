# coding=utf-8
import logging
import re

import discord

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.util import validate_regex

log = logging.getLogger(__name__)


class AntispamPlugin(PluginBase):
    requires_admin = True

    @command(
        "antispam$",
        permission_name="antispam.status",
        description="Lists the count of blackliist/warning entries."
    )
    async def antispam_status(self, message):
        result = "Blacklist {blacklist} entries.\nWarnlist {warnlist} entries.".format(
            blacklist=await self.redis.scard("antispam:{}:blacklist".format(message.server.id)),
            warnlist=await self.redis.scard("antispam:{}:warnlist".format(message.server.id)),
        )
        return Message(result)

    @command(
        "antispam exclude",
        permission_name="antispam.alter.exclude",
        description="Gets the status of the NSFW filter."
    )
    async def exclude_channel(self, message):
        excluded = await self.redis.sismember("antispam:{}:excluded".format(message.server.id), message.channel.id)
        await self._alter_list(message.server, message.channel.id, list_name="excluded", add=not excluded, validate=False)
        return Message("Channel is {action} antispam!".format(
            action="added to" if excluded else "excluded from"
        ))

    @command(
        patterns=[
            r"antispam (?P<action>add|remove) (?P<list>blacklist|warnlist) (?P<filter>.+)",
            r"antispam (?P<list>blacklist|warnlist) (?P<action>add|remove) (?P<filter>.+)"
        ],
        permission_name="antispam.alter.lists",
        description="Adds and removes regexes from the antispam filter."
    )
    async def alter_list(self, message, match):
        action = True if match.group("action") == "add" else False
        return await self._alter_list(message.server, match.group("filter"), list_name=match.group("list"), add=action)

    async def _alter_list(self, server, value, list_name="warnlist", add=True, validate=True):
        action = self.redis.sadd if add else self.redis.srem

        if validate and not validate_regex(value):
            return Message("invalid [make this user friendly l8r]")

        await action("antispam:{}:{}".format(server.id, list_name), [value])
        return Message("List updated!")

    @command(
        patterns=[
            r"antispam list (blacklist|warnlist|warnings|warns)",
            r"antispam (blacklist|warnlist|warnings|warns) list"
        ],
        permission_name="antispam.status",
        description="Lists entries in the blacklist/warnlist."
    )
    async def list_list(self, message, args):
        list_name = ""

        if "black" in args[0].lower():
            list_name = "blacklist"
        elif "warn" in args[0].lower():
            list_name = "warnlist"

        return await self._list_list(message.server, list_name)

    async def _list_list(self, server, list_name):
        list_key = "antispam:{}:{}".format(server.id, list_name)

        contents = await self.redis.smembers(list_key)
        contents = await contents.asset()

        result = "**__{}__**\n".format(
            list_key.split(":")[-1].capitalize()
        )
        result += "\n".join(contents if contents else {"No entries exist in the {}!".format(list_name)})

        return Message(result)

    def create_antispam_embed(self, message: discord.Message, event_type):
        if event_type == "warning":
            icon = "warning"
            colour = discord.Colour.gold()
        else:
            icon = "x_circle"
            colour = discord.Colour.red()

        return discord.Embed(
            colour=colour,
            title=f"{event_type.capitalize()} phrase"
        ).set_thumbnail(
            url=f"https://nepeat.github.io/assets/icons/{icon}.png"
        ).add_field(
            name="Channel",
            value=f"<#{message.channel.id}>"
        ).add_field(
            name="User",
            value=message.author.mention
        ).add_field(
            name="Message",
            value=(message.clean_content[:900] + '...') if len(message.clean_content) > 900 else message.clean_content
        )

    async def on_message(self, message):
        # We cannot run in PMs :(

        if not message.server:
            return

        log_channel = self.bot.get_channel(await self.bot.redis.hget(f"{message.server.id}:settings", "log_channel"))
        if not log_channel:
            return

        if await self.redis.sismember("antispam:{}:excluded".format(message.server.id), message.channel.id):
            return

        if await self.check_list(message, "warnlist"):
            embed = self.create_antispam_embed(message, "warning")
            await self.bot.send_message(log_channel, embed=embed)
        elif await self.check_list(message, "blacklist"):
            if not message.author.server_permissions.administrator:
                await self.bot.delete_message(message)
            embed = self.create_antispam_embed(message, "blacklist")
            await self.bot.send_message(log_channel, embed=embed)

    async def check_list(self, message, list_name):
        items = await self.redis.smembers("antispam:{}:{}".format(message.server.id, list_name))
        items = await items.asset()

        for item in items:
            if re.search(item, message.clean_content, (re.I | re.M)):
                return True

        return False

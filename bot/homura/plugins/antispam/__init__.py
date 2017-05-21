# coding=utf-8
import logging
import re

import discord
from homura.lib.structure import Message
from homura.lib.util import validate_regex
from homura.plugins.antispam import images
from homura.plugins.antispam.signals import AntispamDelete, AntispamWarning, AntispamKick, AntispamBan
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class AntispamPlugin(PluginBase):
    requires_admin = True

    @command(
        "antispam$",
        permission_name="antispam.status",
        description="Lists the count of blackliist/warning entries.",
        usage="antispam"
    )
    async def antispam_status(self, message):
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Antispam status"
        ).add_field(
            name="Blacklist entries",
            value=await self.redis.scard("antispam:{}:blacklist".format(message.guild.id)),
        ).add_field(
            name="Warnlist entries",
            value=await self.redis.scard("antispam:{}:warnlist".format(message.guild.id)),
        )

        return Message(embed)

    @command(
        "antispam exclude$",
        permission_name="antispam.alter.exclude",
        description="Excludes a channel from antispam.",
        usage="antispam exclude"
    )
    async def exclude_channel(self, message):
        excluded = await self.redis.sismember("antispam:{}:excluded".format(message.guild.id), message.channel.id)
        await self._alter_list(message.guild, message.channel.id, list_name="excluded", add=not excluded, validate=False)
        return Message("Channel is {action} antispam!".format(
            action="added to" if excluded else "excluded from"
        ))

    @command(
        patterns=[
            r"antispam (?P<action>add|remove) (?P<list>blacklist|warnlist) (?P<filter>.+)",
            r"antispam (?P<list>blacklist|warnlist) (?P<action>add|remove) (?P<filter>.+)"
        ],
        permission_name="antispam.alter.lists",
        description="Adds and removes regexes from the antispam filter.",
        usage="antispam [blacklist|warnlist] [add|remove] [filter]"
    )
    async def alter_list(self, message, match):
        action = True if match.group("action") == "add" else False
        return await self._alter_list(message.guild, match.group("filter"), list_name=match.group("list"), add=action)

    async def _alter_list(self, guild, value, list_name="warnlist", add=True, validate=True):
        action = self.redis.sadd if add else self.redis.srem

        if validate and not validate_regex(value):
            return Message("invalid [make this user friendly l8r]")

        await action("antispam:{}:{}".format(guild.id, list_name), [value])
        return Message("List updated!")

    @command(
        patterns=[
            r"antispam list (blacklist|warnlist|warnings|warns)",
            r"antispam (blacklist|warnlist|warnings|warns) list"
        ],
        permission_name="antispam.status",
        description="Lists entries in the blacklist/warnlist.",
        usage="antispam [blacklist|warnlist] list"
    )
    async def list_list(self, message, args):
        list_name = ""

        if "black" in args[0].lower():
            list_name = "blacklist"
        elif "warn" in args[0].lower():
            list_name = "warnlist"

        return await self._list_list(message.guild, list_name)

    async def _list_list(self, guild, list_name):
        list_key = "antispam:{}:{}".format(guild.id, list_name)

        contents = await self.redis.smembers_asset(list_key)

        result = "**__{}__**\n".format(
            list_key.split(":")[-1].capitalize()
        )
        result += "\n".join(contents if contents else {"No entries exist in the {}!".format(list_name)})

        return Message(result)

    @staticmethod
    def create_antispam_embed(message: discord.Message, event_type):
        if event_type == "warning":
            icon = event_type.lower()
            colour = discord.Colour.gold()
        elif event_type == "kick" or event_type.endswith("_kick"):
            event_type = event_type.rstrip("_kick")
            icon = "kick"
            colour = discord.Colour.gold()
        else:
            if event_type == "ban" or event_type.endswith("_ban"):
                event_type = event_type.rstrip("_ban")
                icon = "ban"
            else:
                icon = "x_circle"
            colour = discord.Colour.red()

        title = f"Antispam - {event_type.capitalize()}"

        return discord.Embed(
            colour=colour,
            title=title
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

    async def log_event(self, message, reason):
        # Do not log quiet deletes
        if reason == "quiet":
            return

        log_channel = self.bot.get_channel(await self.redis.hget(f"{message.guild.id}:settings", "log_channel"))

        if not log_channel:
            return

        embed = self.create_antispam_embed(message, reason)
        await log_channel.send(embed=embed)

    async def check_lists(self, message):
        if await self.check_list(message, "blacklist"):
            raise AntispamDelete("blacklist")
        elif await self.check_list(message, "warnlist"):
            raise AntispamWarning("warning")

    async def check_list(self, message, list_name):
        items = await self.redis.smembers_asset("antispam:{}:{}".format(message.guild.id, list_name))

        for item in items:
            if re.search(item, message.clean_content, (re.I | re.M)):
                return True

        return False

    async def check_mention_spam(self, message: discord.Message):
        if not message.mentions:
            return False

        user_mentions_key = "antispam:{}:{}:mentions".format(
            message.guild.id,
            message.author.id
        )
        channel_mentions_key = "antispam:{}:{}:mentions".format(
            message.guild.id,
            message.channel.id
        )

        # Increment and expire keys.
        user_mentions_total = await self.redis.incrby(user_mentions_key, len(message.mentions))
        await self.redis.expire(user_mentions_key, 5)
        channel_mentions_total = await self.redis.incrby(channel_mentions_key, len(message.mentions))
        await self.redis.expire(channel_mentions_key, 5)


        if user_mentions_total > 15:
            raise AntispamBan("mentions")
        elif user_mentions_total > 25:
            raise AntispamKick("mentions")

        if channel_mentions_total > 25:
            raise AntispamDelete("mentions")

    async def on_message(self, message):
        # We cannot run in PMs :(
        if not message.guild:
            return

        # Ignore messages that we have excluded.
        if await self.redis.sismember("antispam:{}:excluded".format(message.guild.id), message.channel.id):
            return

        try:
            # Mention checking
            await self.check_mention_spam(message)

            # Image only channel checking
            if await self.redis.sismember("antispam:imagechannels", message.channel.id):
                await images.check(self.bot.aiosession, message)

            # Blacklist / Warning checking
            await self.check_lists(message)
        except AntispamDelete as e:
            if not message.author.guild_permissions.administrator:
                await self.bot.delete_message(message)

            await self.log_event(message, str(e))
        except AntispamWarning:
            await self.log_event(message, "warning")
        except AntispamBan as e:
            await self.bot.delete_message(message)
            await message.author.ban(
                reason=f"Automated ban. Ban criteria was `{str(e)}`"
            )
            await self.log_event(message, str(e) + "_ban")
        except AntispamKick as e:
            await self.bot.delete_message(message)
            await message.author.kick(
                reason=f"Automated kick. Kick criteria was `{str(e)}`"
            )
            await self.log_event(message, str(e) + "_kick")

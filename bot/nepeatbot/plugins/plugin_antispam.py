import re
import discord
import logging

from nepeatbot.plugins.common import PluginBase, command

log = logging.getLogger(__name__)

class AntispamPlugin(PluginBase):
    @command("antispam status")
    async def antispam_status(self, message):
        await self.bot.send_message(message.channel, "not implemented")

    @command("antispam setlog")
    async def set_log(self, message):
        await self.redis.hset("antispam:{}:config".format(message.server.id), "log_channel", message.channel.id)
        await self.bot.send_message(message.channel, "Log channel set!")

    @command("antispam list blacklist")
    async def list_blacklist(self, message):
        await self.bot.send_message(message.channel, "not implemented")

    @command("antispam blacklist (add|remove) (.+)")
    async def alter_blacklist(self, message, args):
        await self.bot.send_message(message.channel, "not implemented")

    @command("antispam list warn(?:s|ing|ings)?")
    async def list_warns(self, message):
        warns = await self.redis.smembers("antispam:{}:warns".format(message.server.id))
        warns = await warns.asset()

        result = "**__Warns__**\n"
        result += "\n".join(warns if warns else {"None"})

        await self.bot.send_message(message.channel, result)

    @command("antispam warnlist (add|remove) (.+)")
    async def alter_warns(self, message, args):
        if args[0] == "add":
            action = self.redis.sadd
        else:
            action = self.redis.srem

        if not self.validate_regex(args[1]):
            self.bot.send_message(message.channel, "invalid warn [make this user friendly l8r]")

        await action("antispam:{}:warns".format(message.server.id), [args[1]])
        await self.bot.send_message(message.channel, "Done!")

    @command("antispam list")
    async def list_help(self, channel):
        await self.bot.send_message(channel, "!antispam list [blacklist|warnings]")

    async def on_message(self, message):
        log_channel_id = await self.redis.hget("antispam:{}:config".format(message.server.id), "log_channel")
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return

        if await self.check_warns(message):
            await self.bot.send_message(log_channel, "\N{WARNING SIGN} **{name}** <#{chat}> {message}".format(
                name=message.author.display_name,
                chat=message.channel.id,
                message=(message.clean_content[:500] + '...') if len(message.clean_content) > 500 else message.clean_content
            ))

    async def check_warns(self, message):
        warns = await self.redis.smembers("antispam:{}:warns".format(message.server.id))
        warns = await warns.asset()

        for warn in warns:
            if re.search(warn, message.clean_content, (re.I | re.M)):
                return True

        return False

    def validate_regex(self, regex):
        try:
            re.compile(regex)
            return True
        except re.error:
            return False

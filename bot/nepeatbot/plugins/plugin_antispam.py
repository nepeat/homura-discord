import re
import discord
import logging

from nepeatbot.plugins.common import PluginBase, Message, command

log = logging.getLogger(__name__)

class AntispamPlugin(PluginBase):
    requires_admin = True

    @command("antispam status")
    async def antispam_status(self, message):
        result = "Blacklist {blacklist} entries.\nWarnlist {warnlist} entries.".format(
            blacklist=await self.redis.scard("antispam:{}:blacklist".format(message.server.id)),
            warnlist=await self.redis.scard("antispam:{}:warnlist".format(message.server.id)),
        )
        return Message(result)

    @command("antispam setlog")
    async def set_log(self, message):
        await self.redis.hset("antispam:{}:config".format(message.server.id), "log_channel", message.channel.id)
        return Message("Log channel set!")

    @command("antispam exclude")
    async def exclude_channel(self, message):
        excluded = await self.redis.sismember("antispam:{}:excluded".format(message.server.id), message.channel.id)
        await self.update_list(message.server, message.channel.id, list_name="excluded", add=not excluded, validate_regex=False)
        return Message("Channel is {action} from antispam!".format(
            action="added" if excluded else "excluded"
        ))

    @command("antispam list blacklist")
    async def list_blacklist(self, message):
        warns = await self.redis.smembers("antispam:{}:blacklist".format(message.server.id))
        warns = await warns.asset()

        result = "**__Blacklist__**\n"
        result += "\n".join(warns if warns else {"None"})

        await self.bot.send_message(message.channel, result)

    @command("antispam blacklist (add|remove) (.+)")
    async def alter_blacklist(self, message, args):
        action = True if args[0] == "add" else False
        return await self.update_list(message.server, args[1], list_name="blacklist", add=action)

    @command("antispam list warn(?:s|ing|ings)?")
    async def list_warns(self, message):
        warns = await self.redis.smembers("antispam:{}:warns".format(message.server.id))
        warns = await warns.asset()

        result = "**__Warns__**\n"
        result += "\n".join(warns if warns else {"None"})

        await self.bot.send_message(message.channel, result)

    @command("antispam warnlist (add|remove) (.+)")
    async def alter_warns(self, message, args):
        action = True if args[0] == "add" else False
        return await self.update_list(message.server, args[1], list_name="warns", add=action)

    @command("antispam list")
    async def list_help(self, channel):
        return Message("!antispam list [blacklist|warnings]")

    async def on_message(self, message):
        log_channel_id = await self.redis.hget("antispam:{}:config".format(message.server.id), "log_channel")
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return

        if await self.redis.sismember("antispam:{}:excluded".format(message.server.id), message.channel.id):
            return

        if await self.check_list(message, "warns"):
            await self.bot.send_message(log_channel, "\N{WARNING SIGN} **{name}** <#{chat}> {message}".format(
                name=self.bot.sanitize(message.author.display_name),
                chat=message.channel.id,
                message=(message.clean_content[:500] + '...') if len(message.clean_content) > 500 else message.clean_content
            ))
        elif await self.check_list(message, "blacklist"):
            if not message.author.server_permissions.administrator:
                await self.bot.delete_message(message)
            await self.bot.send_message(log_channel, "\N{NO ENTRY SIGN} **{name}** <#{chat}> {message}".format(
                name=self.bot.sanitize(message.author.display_name),
                chat=message.channel.id,
                message=(message.clean_content[:500] + '...') if len(message.clean_content) > 500 else message.clean_content
            ))

    async def update_list(self, server, value, list_name="warns", add=True, validate_regex=True):
        action = self.redis.sadd if add else self.redis.srem

        if validate_regex and not self.validate_regex(value):
            return Message("invalid [make this user friendly l8r]")

        await action("antispam:{}:{}".format(server.id, list_name), [value])
        return Message("List updated!")

    async def check_list(self, message, list_name):
        items = await self.redis.smembers("antispam:{}:{}".format(message.server.id, list_name))
        items = await items.asset()

        for item in items:
            if re.search(item, message.clean_content, (re.I | re.M)):
                return True

        return False

    def validate_regex(self, regex):
        try:
            re.compile(regex)
            return True
        except re.error:
            return False

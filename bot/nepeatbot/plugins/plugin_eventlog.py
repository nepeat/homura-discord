import os
import json
import logging
import aiohttp

from nepeatbot.plugins.common import PluginBase, Message, command
from nepeatbot.util import sanitize

log = logging.getLogger(__name__)

class EventLogPlugin(PluginBase):
    requires_admin = True
    EVENTS = ["join", "leave", "server_rename", "member_rename", "message_edit", "message_delete"]

    @command("eventlog setchannel")
    async def set_log(self, message):
        await self.redis.set("channellog:{}:channel".format(message.server.id), message.channel.id)
        return Message("Event log channel set!")

    @command("eventlog")
    async def eventlog(self, message):
        enabled = await self.bot.redis.smembers("channellog:{}:enabled".format(message.server.id))
        enabled = await enabled.asset()

        return Message("**__Enabled__**\n{enabled}\n**__Disabled__**\n{disabled}".format(
            enabled="\n".join(enabled),
            disabled="\n".join([x for x in EventLogPlugin.EVENTS if x not in enabled])
        ))

    @command("eventlog (enable|disable) (.+)")
    async def toggle_event(self, message, args):
        enabled = await self.bot.redis.smembers("channellog:{}:enabled".format(message.server.id))
        enabled = await enabled.asset()

        action = self.bot.redis.sadd if args[0] == "enable" else self.bot.redis.srem

        if args[1] == "all":
            await action("channellog:{}:enabled".format(message.server.id), EventLogPlugin.EVENTS)
        else:
            await action("channellog:{}:enabled".format(message.server.id), [args[1]])

        return Message("Done!")

    async def on_member_join(self, member):
        await self.log_member(member, True)

    async def on_member_remove(self, member):
        await self.log_member(member, False)

    async def on_server_update(self, before, after):
        if before.name != after.name:
            await self.log("\N{MEMO} Server has been renamed from **{before}** to **{after}**".format(
                before=sanitize(before.name),
                after=sanitize(after.name)
            ), before, "server_rename")

    async def on_member_update(self, before, after):
        old = before.nick if before.nick else before.name
        new = after.nick if after.nick else after.name

        if old == new:
            return

        await self.log("\N{MEMO} **{before}** is now known as **{after}**".format(
            before=sanitize(old),
            after=sanitize(new)
        ), before.server, "member_rename")

    async def on_message_edit(self, before, after):
        # Ignore self messages.
        if before.author == self.bot.user:
            return

        if before.content == after.content:
            return

        await self.log("\N{PENCIL} **{user}** has edited their message in __{chat}__".format(
            user=before.author.display_name,
            chat=before.channel.name
        ), before.server, "message_edit")

        await self.log("**__Before__**\n```{message}```".format(
            message=before.clean_content
        ), before.server, "message_edit")

        await self.log("**__After__**\n```{message}```".format(
            message=after.clean_content
        ), before.server, "message_edit")

    async def on_message_delete(self, message):
        if message.author == self.bot.user:
            return

        if await self.redis.sismember("ignored:{}".format(message.server.id), message.id):
            return

        await self.log("\N{PUT LITTER IN ITS PLACE SYMBOL} __{chat}__ `{user}` - {message}".format(
            chat=message.channel.name,
            user=message.author.display_name,
            message=message.clean_content
        ), message.server, "message_delete")

    async def push_event(self, event_type, server=None, channel=None, data=None, endpoint="push"):
        payload = {
            "type": event_type,
            "server": server.id if server else None,
            "channel": channel.id if channel else None,
            "data": data if data else {}
        }

        try:
            async with self.bot.aiosession.post(
                url=self.events_url + "/events/" + endpoint,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("status") == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
        except aiohttp.errors.ClientError:
            return False

    async def get_events(self, event_type, server, channel=None):
        params = {
            "server": server.id,
        }

        if channel:
            params.update({"channel": channel.id})

        log.debug(event_type)
        log.debug(params)

        try:
            async with self.bot.aiosession.get(
                url=self.events_url + "/events/" + event_type,
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("status") == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
                        return None
                    return reply.get("events", None)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    pass
        except aiohttp.errors.ClientError:
            pass

        return None

    async def log(self, message, server, event_type):
        log_channel_id = await self.redis.get("channellog:{}:channel".format(server.id))
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return

        enabled = await self.redis.sismember("channellog:{}:enabled".format(server.id), event_type)
        if enabled:
            await self.bot.send_message(log_channel, message)

    async def log_member(self, member, joining):
        await self.log("{emote} `{user}` has {action}.".format(
            emote="\N{WHITE HEAVY CHECK MARK}" if joining else "\N{DOOR}",
            user=member.display_name,
            action="joined" if joining else "left"
        ), member.server, "join" if joining else "leave")

# coding=utf-8
import logging

import discord

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.util import sanitize

log = logging.getLogger(__name__)


class EventLogPlugin(PluginBase):
    requires_admin = True
    EVENTS = ["join", "leave", "server_rename", "member_rename", "message_edit", "message_delete"]

    @command(
        "eventlog",
        permission_name="eventlog.status",
        description="Shows what events are being logged.",
        usage="eventlog"
    )
    async def eventlog(self, message):
        enabled = await self.redis.smembers_asset("channellog:{}:enabled".format(message.server.id))

        return Message("**__Enabled__**\n{enabled}\n**__Disabled__**\n{disabled}".format(
            enabled="\n".join(enabled),
            disabled="\n".join([x for x in EventLogPlugin.EVENTS if x not in enabled])
        ))

    @command(
        "eventlog (enable|disable) (.+)",
        permission_name="eventlog.toggle",
        description="Toggles what events to log.",
        usage="eventlog [enable|disable]"
    )
    async def toggle_event(self, message, args):
        enabled = await self.redis.smembers_asset("channellog:{}:enabled".format(message.server.id))

        action = self.redis.sadd if args[0] == "enable" else self.redis.srem

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
            embed = discord.Embed(
                colour=discord.Colour.gold(),
                title=f"Server has been renamed"
            ).set_thumbnail(
                url="https://nepeat.github.io/assets/icons/edit.png"
            ).add_field(
                name="Before",
                value=sanitize(before.name)
            ).add_field(
                name="After",
                value=sanitize(after.name)
            )
            await self.log(embed, before, "server_rename")

    async def on_member_update(self, before, after):
        old = before.nick if before.nick else before.name
        new = after.nick if after.nick else after.name

        if old == new:
            return

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"User name change"
        ).set_thumbnail(
            url="https://nepeat.github.io/assets/icons/edit.png"
        ).add_field(
            name="Before",
            value=sanitize(old),
            inline=False
        ).add_field(
            name="After",
            value=sanitize(new),
            inline=False
        )

        await self.log(embed, before.server, "member_rename")

    async def on_message_edit(self, before, after):
        # Ignore self messages.
        if before.author == self.bot.user:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"Message has been edited"
        ).set_thumbnail(
            url="https://nepeat.github.io/assets/icons/edit.png"
        ).add_field(
            name="Channel",
            value=before.channel.mention
        ).add_field(
            name="User",
            value=before.author.mention
        ).add_field(
            name="Before",
            value=(before.clean_content[:900] + '...') if len(before.clean_content) > 900 else before.clean_content
        ).add_field(
            name="After",
            value=(after.clean_content[:900] + '...') if len(after.clean_content) > 900 else after.clean_content
        )

        await self.log(embed, before.server, "message_edit")

    async def on_message_delete(self, message):
        if message.author == self.bot.user:
            return

        if await self.redis.sismember("ignored:{}".format(message.server.id), message.id):
            return

        # Check: Webhooks have no display name.

        if not message.author.display_name:
            return

        # Check: There must be a message text.

        if not message.clean_content:
            return

        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f"Deleted message"
        ).set_thumbnail(
            url="https://nepeat.github.io/assets/icons/trash.png"
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

        await self.log(embed, message.server, "message_delete")

    async def log(self, message, server, event_type):
        log_channel = self.bot.get_channel(await self.redis.hget(f"{server.id}:settings", "log_channel"))
        if not log_channel:
            return

        enabled = await self.redis.sismember("channellog:{}:enabled".format(server.id), event_type)
        if enabled:
            if isinstance(message, discord.Embed):
                await self.bot.send_message(log_channel, embed=message)
            else:
                await self.bot.send_message(log_channel, message)

    async def log_member(self, member, joining):
        embed = discord.Embed(
            colour=discord.Colour.green() if joining else discord.Colour.red(),
            title=f"{member.display_name} has {'joined' if joining else 'left'}"
        ).set_thumbnail(
            url=f"https://nepeat.github.io/assets/icons/{'check' if joining else 'x_circle'}.png"
        ).add_field(
            name="Mention",
            value=member.mention
        )

        await self.log(embed, member.server, "join" if joining else "leave")

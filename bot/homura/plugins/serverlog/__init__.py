# coding=utf-8
import json
import logging
import os
from typing import Optional

import aiohttp
import discord

from homura.lib.util import sanitize
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class ServerLogPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events_url = os.environ.get("BOT_WEB", "http://localhost:5000")

    @command(
        "undelete",
        permission_name="serverlog.undelete",
        description="Undeletes messages in a channel.",
        requires_admin=True,
        usage="undelete"
    )
    async def cmd_undelete(self, message, bot):
        messages = await self.get_events("delete", message.guild, message.channel)
        if not messages:
            return await message.channel.send("None")

        output = "\n".join(["__{sender}__ - {message}".format(
            sender=sanitize(event["data"]["sender"]["display_name"]),
            message=sanitize(event["data"]["message"])
        ) for event in messages])

        await message.channel.send(output)

    async def on_ready(self):
        await self.add_all_guilds()

    async def on_member_join(self, member):
        await self.log_member(member, True)

    async def on_member_remove(self, member):
        await self.log_member(member, False)

    async def on_guild_join(self, guild):
        await self.push_event("guild_join", guild, None, {
            "server": {
                "name": guild.name
            }
        })

    async def on_guild_update(self, before, after):
        if before.name != after.name:
            await self.push_event("rename_guild", before, None, {
                "server": {
                    "before": before.name,
                    "after": after.name,
                }
            })

    async def on_member_update(self, before, after):
        old = before.nick if before.nick else before.name
        new = after.nick if after.nick else after.name

        if old == new:
            return

        await self.push_event("rename", before.guild, None, {
            "sender": {
                "id": str(before.id)
            },
            "nick": {
                "old": old,
                "new": new
            }
        })

    async def on_channel_update(self, before, after):
        if before.topic != after.topic:
            await self.push_event("topic", before.guild, before, {
                "topic": {
                    "before": before.topic,
                    "after": after.topic,
                }
            })

        if before.name != after.name:
            await self.push_event("rename_channel", before.guild, before, {
                "channel": {
                    "before": before.name,
                    "after": after.name,
                }
            })

    async def on_message_edit(self, before, after):
        # Ignore self messages.
        if before.author == self.bot.user:
            return

        if before.content == after.content:
            return

        await self.push_event("edit", before.guild, before.channel, {
            "sender": {
                "id": str(before.author.id),
                "display_name": before.author.display_name,
            },
            "edit": {
                "before": before.clean_content,
                "after": after.clean_content,
            }
        })

    async def on_message_delete(self, message):
        await self.push_event("delete", message.guild, message.channel, {
            "sender": {
                "id": str(message.author.id),
                "display_name": message.author.display_name,
            },
            "message": message.clean_content
        })

    async def push_event(
        self,
        event_type: str,
        guild: Optional[discord.Guild]=None,
        channel: Optional[discord.abc.Messageable]=None,
        data: dict=None
    ):
        payload = {
            "server": guild.id if guild else None,
            "channel": channel.id if channel else None,
            "data": data if data else {}
        }

        try:
            async with self.bot.aiosession.put(
                url=self.events_url + "/api/events/" + event_type,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            ) as response:
                try:
                    reply = await response.json()
                    if response.status in (400, 500):
                        log.error("Error pushing event to server.")
                        log.error(reply)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
        except aiohttp.ClientError:
            return False

    async def get_events(self, event_type, guild, channel=None):
        params = {
            "server": guild.id,
        }

        if channel:
            params.update({"channel": channel.id})

        log.debug(event_type)
        log.debug(params)

        try:
            async with self.bot.aiosession.get(
                url=self.events_url + "/api/events/" + event_type,
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if response.status in (400, 500):
                        log.error("Error pushing event to server.")
                        log.error(reply)
                        return None
                    return reply.get("events", None)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    pass
        except aiohttp.ClientError:
            pass

        return None

    async def log_member(self, member, joining):
        action = "join" if joining else "leave"

        await self.push_event(action, member.guild, None, {
            "id": member.id,
            "name": member.name
        })

    async def add_all_guilds(self):
        payload = {}

        for guild in self.bot.guilds:
            payload[str(guild.id)] = {
                "name": guild.name,
                "channels": {}
            }

            for channel in guild.channels:
                payload[str(guild.id)]["channels"][str(channel.id)] = channel.name

        await self.push_event("bulk", data=payload)

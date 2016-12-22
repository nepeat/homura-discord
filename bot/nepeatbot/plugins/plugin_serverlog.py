import os
import json
import logging
import aiohttp

import discord
from typing import Optional

from nepeatbot.plugins.common import PluginBase, command
from nepeatbot.util import sanitize

log = logging.getLogger(__name__)


class ServerLogPlugin(PluginBase):
    is_global = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events_url = os.environ.get("BOT_WEB", "http://localhost:5000")

    @command("undelete", requires_admin=True)
    async def cmd_undelete(self, message, bot):
        messages = await self.get_events("delete", message.server, message.channel)
        if not messages:
            return await bot.send_message(message.channel, "None")

        output = "\n".join(["__{sender}__ - {message}".format(
            sender=sanitize(event["data"]["sender"]["display_name"]),
            message=sanitize(event["data"]["message"])
        ) for event in messages])

        await bot.send_message(message.channel, output)

    async def on_ready(self):
        await self.add_all_servers()

    async def on_member_join(self, member):
        await self.log_member(member, True)

    async def on_member_remove(self, member):
        await self.log_member(member, False)

    async def on_server_update(self, before, after):
        if before.name != after.name:
            await self.push_event("rename_server", before, None, {
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

        await self.push_event("rename", before.server, None, {
            "old": old,
            "new": new
        })

    async def on_channel_update(self, before, after):
        if before.topic != after.topic:
            await self.push_event("topic", before.server, before, {
                "topic": {
                    "before": before.topic,
                    "after": after.topic,
                }
            })

        if before.name != after.name:
            await self.push_event("rename_channel", before.server, before, {
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

        await self.push_event("edit", before.server, before.channel, {
            "sender": {
                "id": before.author.id,
                "display_name": before.author.display_name,
            },
            "edit": {
                "before": before.clean_content,
                "after": after.clean_content,
            }
        })

    async def on_message_delete(self, message):
        if message.author == self.bot.user:
            return

        await self.push_event("delete", message.server, message.channel, {
            "sender": {
                "id": message.author.id,
                "display_name": message.author.display_name,
            },
            "message": message.clean_content
        })

    async def push_event(
        self,
        event_type: str,
        server: Optional[discord.Server]=None,
        channel: Optional[discord.Channel]=None,
        data: dict=None
    ):
        payload = {
            "server": server.id if server else None,
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
        except aiohttp.errors.ClientError:
            pass

        return None

    async def log_member(self, member, joining):
        action = "join" if joining else "leave"

        await self.push_event(action, member.server, None, {
            "name": member.name
        })

    async def add_all_servers(self):
        payload = {}

        for server in self.bot.servers:
            payload[server.id] = server.name

        await self.push_event("bulk", data=payload)

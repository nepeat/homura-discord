# coding=utf-8
import datetime
import time
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

    @command(
        "archivechannel",
        permission_name="serverlog.archive.channel",
        description="Does a full archival of a channel.",
        requires_admin=True,
        usage="archivechannel"
    )
    async def cmd_archivechannel(self, message, bot):
        await self.archive_channel(message.channel)
        await message.channel.send("Complete!")

    @command(
        "archiveserver",
        permission_name="serverlog.archive.server",
        description="Does a full archival of the whole server.",
        requires_admin=True,
        usage="archiveserver"
    )
    async def cmd_archiveserver(self, message, bot):
        for channel in message.guild.text_channels:
            await self.archive_channel(channel)
            await message.channel.send(f"Completed archiving #{channel.name}!")
        await message.channel.send("Full archive complete!")

    async def archive_channel(self, channel: discord.abc.Messageable):
        # Grab the before date from Redis if it exists.
        stored_date = await self.redis.get(f"archive:{channel.id}")

        try:
            before_date = datetime.datetime.utcfromtimestamp(float(stored_date))
        except (ValueError, TypeError):
            before_date = datetime.datetime.utcnow()

        i = 0
        payload = []
        async for message in channel.history(before=before_date, limit=None):
            i += 1

            # Add the message to the payload queue.
            payload.append({
                "id": message.id,
                "author_id": message.author.id,
                "server_id": message.guild.id,
                "channel_id": message.channel.id,
                "tts": message.tts,
                "pinned": message.pinned,
                "attachments": self.dump_attachments(message),
                "reactions": self.dump_reactions(message),
                "embeds": self.dump_embeds(message),
                "created": message.created_at.timestamp() if message.created_at else None,
                "edited": message.edited_at.timestamp() if message.edited_at else None,
                "message": message.content
            })

            # Set the latest message if we are on the first message.
            if i == 1:
                await self.redis.hset("archive:state", channel.id, message.id)

            # Upload the buffer every 200 messages.
            if i % 200 == 0:
                status = await self.push_event("bulk_channel", data=payload)
                if not status:
                    await self.redis.sadd(f"archive:fails:{channel.id}", str(time.time()))
                payload.clear()

            # Store the timestamp every 400 messages.
            if i % 400 == 0:
                log.info(f"Processed {i} messages for channel {channel.id}")
                await self.redis.set(f"archive:{channel.id}", message.created_at.timestamp())

        # Finish the upload if we still have a payload.
        if payload:
            await self.push_event("bulk_channel", data=payload)

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

    async def on_message(self, message):
        # Set the latest message.
        await self.redis.hset("archive:state", message.channel.id, message.id)

        # XXX: Deduplicate this later in the morning.
        payload = []
        payload.append({
            "id": message.id,
            "author_id": message.author.id,
            "server_id": message.guild.id,
            "channel_id": message.channel.id,
            "tts": message.tts,
            "pinned": message.pinned,
            "attachments": self.dump_attachments(message),
            "reactions": self.dump_reactions(message),
            "embeds": self.dump_embeds(message),
            "created": message.created_at.timestamp() if message.created_at else None,
            "edited": message.edited_at.timestamp() if message.edited_at else None,
            "message": message.content
        })
        await self.push_event("bulk_channel", data=payload)

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
                        return False
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    return False

        except aiohttp.ClientError:
            return False

        return True

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
                        log.error("Error getting events from server.")
                        log.error(reply)
                        return False

                    return reply.get("events", False)
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    return False

        except aiohttp.ClientError:
            return False

        return True

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

    def dump_attachments(self, message: discord.Message):
        if not message.attachments:
            return []

        attachments = []
        for attachment in message.attachments:
            attachments.append({
                "id": attachment.id,
                "filename": attachment.filename,
                "url": attachment.url
            })

        return attachments

    def dump_embeds(self, message: discord.Message):
        if not message.embeds:
            return []

        embeds = []
        for embed in message.embeds:
            embeds.append(embed.to_dict())

        return embeds

    def dump_reactions(self, message: discord.Message):
        if not message.reactions:
            return []

        reactions = []
        for reaction in message.reactions:
            reactions.append({
                "emoji": str(reaction.emoji),
                "cont": reaction.count or 0
            })

        return reactions

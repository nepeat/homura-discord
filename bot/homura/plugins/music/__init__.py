import logging

import discord

from homura.plugins.common import Message
from homura.plugins.music.commands import MusicCommands

log = logging.getLogger(__name__)

# Thanks Rhino bot!

class MusicPlugin(MusicCommands):
    # Discord events

    async def on_ready(self):
        for channel_id in await self.bot.redis.smembers_asset("music:reload"):
            voice_channel = self.bot.get_channel(channel_id)
            if voice_channel:
                await self.bot.join_voice_channel(voice_channel)
                await self.get_player(voice_channel.server)
            await self.bot.redis.spop("music:reload")

    async def on_logout(self):
        log.info("Got logout event!")
        await self.cleanup_voice_clients()

    # Music events

    async def on_player_play(self, player, entry):
        channel = entry.meta.get("channel", None)
        author = entry.meta.get("author", None)

        if channel and author:
            next = player.playlist.peek()

            embed = discord.Embed(
                colour=discord.Colour.orange(),
                title="Music",
            ).add_field(
                name="Now playing",
                value=entry.title,
                inline=False
            ).add_field(
                name="Up next",
                value=next.title if next else "Nothing!",
                inline=False
            )

            await self.bot.send_message_object(Message(embed=embed), channel)

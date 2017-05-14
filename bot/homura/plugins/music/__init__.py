# coding=utf-8
import asyncio
import logging

from homura.lib.structure import Message
from homura.plugins.music.commands import MusicCommands

log = logging.getLogger(__name__)

# Thanks Rhino bot!


class MusicPlugin(MusicCommands):
    # Discord events

    async def on_ready(self):
        for channel_id in await self.bot.redis.smembers_asset("music:reload"):
            voice_channel = self.bot.get_channel(int(channel_id))
            if voice_channel:
                try:
                    await voice_channel.connect(timeout=5)
                except asyncio.TimeoutError:
                    await asyncio.sleep(2)
                    await voice_channel.connect(timeout=5)

                await self.get_player(voice_channel.guild)
            await self.bot.redis.spop("music:reload")

    async def on_logout(self):
        log.info("Got logout event!")
        await self.cleanup_players()

    # Music events

    async def on_player_play(self, player, entry):
        player.skip_state.reset()

        channel = entry.meta.get("channel", None)
        author = entry.meta.get("author", None)

        if channel and author:
            next_entry = player.playlist.peek()

            embed = self.create_voice_embed().add_field(
                name="Now playing",
                value=entry.title,
                inline=False
            ).add_field(
                name="Up next",
                value=next_entry.title if next_entry else "Nothing!",
                inline=False
            )

            await self.bot.send_message_object(Message(embed), channel)

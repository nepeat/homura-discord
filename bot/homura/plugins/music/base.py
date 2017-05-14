# coding=utf-8
import asyncio
import os

import discord

from homura.lib.structure import CommandError
from homura.plugins.base import PluginBase
from homura.plugins.music.downloader import Downloader
from homura.plugins.music.player import Player
from homura.plugins.music.playlist import Playlist


class MusicBase(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.players = {}
        self.downloader = Downloader(self.bot, os.environ.get("AUDIO_CACHE_PATH", "audio_cache"))
        self.loop.create_task(self.inactive_purger())

    async def inactive_purger(self):
        checks = {}

        while True:
            for guild_id, player in self.players.copy().items():
                if guild_id not in checks:
                    checks[guild_id] = 0

                # Nobody has joined for almost two minutes, bye client!
                if checks[guild_id] == 3:
                    checks[guild_id] = 0
                    await self.cleanup_player(player)
                    continue

                if len(player.voice_client.channel.members) == 1:
                    # We are the only one in the channel, strike!
                    checks[guild_id] += 1
                else:
                    # Reset the counter if there is more people than us.
                    checks[guild_id] = 0

            await asyncio.sleep(60)

    @staticmethod
    def create_voice_embed(description=None, colour=discord.Colour.blue(), title=None):
        if not title:
            title = "Music"
        else:
            title = "Music - " + title

        return discord.Embed(
            colour=colour,
            title=title,
            description=description
        )

    async def get_voice_client(self, guild: discord.Guild, member: discord.Member=None):
        if guild.voice_client:
            return guild.voice_client
        else:
            if not member:
                raise CommandError("Bot is not in a voice channel.")

            if not member.voice:
                raise CommandError("You must be in a channel to summon the bot!")

            voice_client = await member.voice.channel.connect()

        return voice_client

    async def get_player(self, guild: discord.Guild, caller: discord.Member=None):
        if guild.id in self.players:
            return self.players[guild.id]
        else:
            voice_client = await self.get_voice_client(guild, caller)

            playlist = Playlist(self, guild)
            player = Player(self, playlist, voice_client)\
                .on("play", self.on_player_play)
            self.players[guild.id] = player

            return player

    async def cleanup_player(self, player):
        try:
            if player.is_playing:
                await self.redis.sadd("music:reload", [player.channel.id])

            player.kill()
            await player.voice_client.disconnect()
        finally:
            del self.players[player.guild.id]

    async def cleanup_players(self):
        for player in self.players.copy().values():
            await self.cleanup_player(player)

    @staticmethod
    def _fixg(x, dp=2):
        return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

# coding=utf-8
import os

import discord

from homura.lib.signals import CommandError
from homura.plugins.common import PluginBase
from homura.plugins.music.downloader import Downloader
from homura.plugins.music.player import Player
from homura.plugins.music.playlist import Playlist


class MusicBase(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.players = {}
        self.downloader = Downloader(self.bot, os.environ.get("AUDIO_CACHE_PATH", "audio_cache"))

    def create_voice_embed(self, description=None, colour=discord.Colour.blue(), title=None):
        if not title:
            title = "Music"
        else:
            title = "Music - " + title

        return discord.Embed(
            colour=colour,
            title=title,
            description=description
        )


    async def get_voice_client(self, server: discord.Server, member: discord.Member=None):
        if server.voice_client:
            return server.voice_client
        else:
            if not member:
                raise CommandError("Bot is not in a voice channel.")

            if not member.voice_channel:
                raise CommandError("You must be in a channel to summon the bot!")

            voice_client = await self.bot.join_voice_channel(member.voice_channel)

        return voice_client

    async def get_player(self, server: discord.Server, caller: discord.Member=None):
        if server.id in self.players:
            return self.players[server.id]
        else:
            voice_client = await self.get_voice_client(server, caller)

            playlist = Playlist(self, server)
            player = Player(self, playlist, voice_client)\
                .on("play", self.on_player_play)
            self.players[server.id] = player

            return player

    async def cleanup_player(self, player):
        try:
            if player.is_playing:
                await self.bot.redis.sadd("music:reload", [player.channel.id])

            player.kill()
            await player.voice_client.disconnect()
        finally:
            del self.players[player.server.id]

    async def cleanup_players(self):
        for player in self.players.copy().values():
            await self.cleanup_player(player)

    @staticmethod
    def _fixg(x, dp=2):
        return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

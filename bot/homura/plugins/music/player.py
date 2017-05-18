# coding=utf-8
import audioop
import functools
import logging
import traceback

from enum import Enum

import asyncio
import discord
from homura.lib.eventemitter import EventEmitter
from homura.plugins.music.objects import SkipState
from typing import Optional

log = logging.getLogger(__name__)


class MusicPlayerState(Enum):
    STOPPED = 0  # When the player isn't playing anything
    PLAYING = 1  # The player is actively playing music.
    PAUSED = 2   # The player is paused on a song.
    WAITING = 3  # The player has finished its song but is still downloading the next one
    DEAD = 4     # The player has been killed.

    def __str__(self):
        return self.name


class HellPCMVolumeTransformer(discord.PCMVolumeTransformer):
    def __init__(self, *args, **kwargs):
        self.frame_count = 0
        super().__init__(*args, **kwargs)

    def read(self):
        self.frame_count += 1
        ret = self.original.read()
        return audioop.mul(ret, 2, self._volume)


class Player(EventEmitter):
    def __init__(self, plugin, playlist, voice_client: discord.VoiceClient):
        super().__init__()

        self.plugin = plugin
        self.loop = plugin.bot.loop
        self.voice_client = voice_client
        self.playlist = playlist
        self.playlist.on("entry-added", self.on_entry_added)
        self._volume = 1.0
        self.skip_state = SkipState()

        self._play_lock = asyncio.Lock()
        self._current_entry = None
        self.state = MusicPlayerState.STOPPED

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        if value == self._volume:
            return

        self._volume = value
        if self.voice_client.source:
            self.voice_client.source.volume = value

    def on_entry_added(self, playlist, entry):
        if self.is_stopped:
            self.loop.call_later(2, self.play)

    def seek(self, time=None):
        entry = self._current_entry

        if not entry:
            return

        if not entry.seekable:
            raise TypeError("You cannot seek this type of video.")

        if time < 0:
            raise ValueError("Cannot seek past negative numbers.")

        if (time > entry.duration) and entry.duration != 0:
            raise ValueError("Seek length is longer than the video.")

        if entry:
            entry.seek = time
            entry.quiet = True
            self.playlist.entries.appendleft(entry)
            self.loop.create_task(self.plugin.bot.redis.lpush(self.playlist.queue_key, [entry.to_json()]))
            self.voice_client.stop()

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()
        else:
            self.after_callback()

    def stop(self):
        self.state = MusicPlayerState.STOPPED
        self.voice_client.stop()

    def resume(self):
        if self.is_paused:
            self.voice_client.resume()
            self.state = MusicPlayerState.PLAYING
            return

        if self.is_paused and not self.voice_client.is_playing():
            self.state = MusicPlayerState.PLAYING
            self.voice_client.stop()
            return

        raise ValueError("Cannot resume playback from state %s" % self.state)

    def pause(self):
        if self.is_playing:
            self.state = MusicPlayerState.PAUSED
            self.voice_client.pause()

            return

        elif self.is_paused:
            return

        raise ValueError("Cannot pause a MusicPlayer in state %s" % self.state)

    def kill(self):
        # Save the current entry before killing the bot.
        current = self.current_entry
        if current:
            current.seek = self.progress

        self.state = MusicPlayerState.DEAD
        self.playlist.clear(kill=True, last_entry=current)
        self._events.clear()
        self.voice_client.stop()

    def after_callback(self, e=None):
        if e and isinstance(e, Exception):
            self.plugin.bot.on_error("music_thread")

        entry = self._current_entry

        if self.voice_client._player:
            self.voice_client._player.after = None

        self._current_entry = None

        if not self.is_stopped and not self.is_dead:
            self.play(_continue=True)

    def play(self, _continue=False):
        self.loop.create_task(self._play(_continue=_continue))

    async def _play(self, _continue=False):
        if self.is_paused:
            return self.resume()

        with await self._play_lock:
            log.debug("is_stop %s continue %s", self.is_stopped, _continue)
            if self.is_stopped or _continue:
                entry = await self.playlist.get_next_entry()

                # If nothing left to play, transition to the stopped state.
                if not entry:
                    log.debug("Could not get entry, stopping player.")
                    self.stop()
                    return

                # In-case there was a player, kill it. RIP.
                if self.voice_client.is_playing():
                    self.voice_client.stop()

                # Set the player options.
                options = "-nostdin -ss {seek}".format(
                    seek=entry.seek
                )

                self.voice_client.play(discord.FFmpegPCMAudio(
                    source=entry.filename,
                    options=options,
                ),
                    # Threadsafe call soon, b/c after will be called from the voice playback thread.
                    after=lambda e: self.loop.call_soon_threadsafe(functools.partial(self.after_callback, e))
                )

                self.voice_client.source = HellPCMVolumeTransformer(self.voice_client.source)
                self.voice_client.volume = self.volume

                self.state = MusicPlayerState.PLAYING
                self._current_entry = entry

                if not entry.quiet:
                    self.emit("play", player=self, entry=entry)

                if entry.seek:
                    self.voice_client.source.frame_count += round(entry.seek / 0.02)


    @property
    def guild(self) -> Optional[discord.Guild]:
        return self.voice_client.guild

    @property
    def channel(self) -> Optional[discord.VoiceChannel]:
        return self.voice_client.channel

    @property
    def current_entry(self):
        return self._current_entry

    @property
    def is_playing(self):
        return self.state == MusicPlayerState.PLAYING

    @property
    def is_paused(self):
        return self.state == MusicPlayerState.PAUSED

    @property
    def is_stopped(self):
        return self.state == MusicPlayerState.STOPPED

    @property
    def is_dead(self):
        return self.state == MusicPlayerState.DEAD

    @property
    def progress(self):
        if self.voice_client.source:
            return round(self.voice_client.source.frame_count * 0.02)

        return 0

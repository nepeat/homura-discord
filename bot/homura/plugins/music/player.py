# coding=utf-8
import asyncio
import logging
from enum import Enum
from typing import Optional

import discord

import audioop
from homura.lib.eventemitter import EventEmitter

log = logging.getLogger(__name__)


class MusicPlayerState(Enum):
    STOPPED = 0  # When the player isn't playing anything
    PLAYING = 1  # The player is actively playing music.
    PAUSED = 2   # The player is paused on a song.
    WAITING = 3  # The player has finished its song but is still downloading the next one
    DEAD = 4     # The player has been killed.

    def __str__(self):
        return self.name


class PatchedBuff(object):
    """
        PatchedBuff monkey patches a readable object, allowing you to vary what the volume is as the song is playing.
    """

    def __init__(self, buff, *args):
        self.buff = buff
        self.frame_count = 0
        self.volume = 1.0

    def read(self, frame_size):
        self.frame_count += 1
        frame = self.buff.read(frame_size)

        if self.volume != 1:
            frame = audioop.mul(frame, 2, self.volume)

        return frame


class Player(EventEmitter):
    def __init__(self, plugin, playlist, voice_client: discord.VoiceClient):
        super().__init__()

        self.plugin = plugin
        self.loop = plugin.bot.loop
        self.voice_client = voice_client
        self.playlist = playlist
        self.playlist.on("entry-added", self.on_entry_added)
        self._volume = 1.0

        self._play_lock = asyncio.Lock()
        self._current_player = None
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
        if self._current_player:
            self._current_player.buff.volume = value

    def on_entry_added(self, playlist, entry):
        if self.is_stopped:
            self.loop.call_later(2, self.play)

    def seek(self, time=None):
        entry = self._current_entry

        if not entry:
            return

        if time < 0:
            raise ValueError("Cannot seek past negative numbers.")

        if (time > entry.duration) and entry.duration != 0:
            raise ValueError("Seek length is longer than the video.")

        if entry:
            entry.seek = time
            entry.quiet = True
            self.playlist.entries.appendleft(entry)
            self.loop.create_task(self.plugin.bot.redis.lpush("music:queue:" + self.voice_client.server.id, [entry.to_json()]))
            self._kill_current_player()

    def skip(self):
        self._kill_current_player()

    def stop(self):
        self.state = MusicPlayerState.STOPPED
        self._kill_current_player()

    def resume(self):
        if self.is_paused and self._current_player:
            self._current_player.resume()
            self.state = MusicPlayerState.PLAYING
            return

        if self.is_paused and not self._current_player:
            self.state = MusicPlayerState.PLAYING
            self._kill_current_player()
            return

        raise ValueError("Cannot resume playback from state %s" % self.state)

    def pause(self):
        if self.is_playing:
            self.state = MusicPlayerState.PAUSED

            if self._current_player:
                self._current_player.pause()

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
        self._kill_current_player()

    def _playback_finished(self):
        entry = self._current_entry

        if self._current_player:
            self._current_player.after = None
            self._kill_current_player()

        self._current_entry = None

        if not self.is_stopped and not self.is_dead:
            self.play(_continue=True)

    def _kill_current_player(self):
        if self._current_player:
            if self.is_paused:
                self.resume()

            try:
                self._current_player.stop()
            except OSError:
                pass
            self._current_player = None
            return True

        return False

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
                self._kill_current_player()

                # Set the player options.
                before_options = "-nostdin -ss {seek}".format(
                    seek=entry.seek
                )

                options = "-vn -b:a 128k"

                self._current_player = self._monkeypatch_player(self.voice_client.create_ffmpeg_player(
                    entry.filename,
                    before_options=before_options,
                    options=options,
                    # Threadsafe call soon, b/c after will be called from the voice playback thread.
                    after=lambda: self.loop.call_soon_threadsafe(self._playback_finished)
                ))
                self._current_player.setDaemon(True)
                self._current_player.buff.volume = self.volume

                self.state = MusicPlayerState.PLAYING
                self._current_entry = entry

                self._current_player.start()
                if not entry.quiet:
                    self.emit("play", player=self, entry=entry)

                if entry.seek:
                    self._current_player.buff.frame_count += round(entry.seek / 0.02)

    def _monkeypatch_player(self, player):
        original_buff = player.buff
        player.buff = PatchedBuff(original_buff)
        return player

    @property
    def server(self) -> Optional[discord.Server]:
        return self.voice_client.server

    @property
    def channel(self) -> Optional[discord.Channel]:
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
        if self._current_player:
            return round(self._current_player.buff.frame_count * 0.02)

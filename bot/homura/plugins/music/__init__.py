import logging
import os
import random

import discord
import traceback
import time
import pytimeparse
from datetime import timedelta
from homura.lib.signals import CommandError
from homura.plugins.common import Message, PluginBase, command
from homura.plugins.music.downloader import Downloader
from homura.plugins.music.player import Player
from homura.plugins.music.playlist import Playlist
from homura.plugins.nsfw.common import API_ENDPOINTS, USER_AGENT
from homura.plugins.nsfw.fetcher import ImageFetcher
from homura.util import sanitize

DISCORD_FIELD_CHAR_LIMIT = 1000
log = logging.getLogger(__name__)

# Thanks Rhino bot!

class MusicPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.players = {}
        self.downloader = Downloader(self.bot, os.environ.get("MUSIC_DOWNLOAD_FOLDER", "audio_cache"))

    @command(
        "music$",
        permission_name="music",
        global_command=True,
        description="Music status"
    )
    async def music(self, message, args):
        player = await self.get_player(message.server, message.author)

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Music"
        )

        if player.current_entry:
            embed.add_field(
                name="Now playing",
                value=player.current_entry.title
            )

            if player.current_entry.meta.get("author", ""):
                embed.add_field(
                    name="Added by",
                    value=player.current_entry.meta["author"].name
                )

            song_progress = str(timedelta(seconds=player.progress)).lstrip('0').lstrip(':')
            song_total = str(timedelta(seconds=player.current_entry.duration)).lstrip('0').lstrip(':')
            prog_str = '%s/%s' % (song_progress, song_total)
            embed.add_field(
                name="Progress",
                value=prog_str
            )

        queue_lines = []
        queue_unlisted = 0
        andmoretext = '* ... and %s more*' % ('x' * len(player.playlist.entries))
        for i, item in enumerate(player.playlist, 1):
            if item.meta.get("author", ""):
                nextline = f"`{i}.` **{item.title}** added by **{item.meta['author'].name}**".strip()
            else:
                nextline = f"`{i}.` **{item.title}**".strip()

            currentlinesum = sum(len(x) + 1 for x in queue_lines)

            if currentlinesum + len(nextline) + len(andmoretext) > DISCORD_FIELD_CHAR_LIMIT:
                if currentlinesum + len(andmoretext):
                    queue_unlisted += 1
                    continue

            queue_lines.append(nextline)

        if queue_unlisted:
            queue_lines.append("\n*... and %s more*" % queue_unlisted)

        if not queue_lines:
            queue_lines.append("There are no songs queued! Queue something with !music play.")

        embed.add_field(
            name="Queue",
            value="\n".join(queue_lines),
            inline=False
        )

        return Message(embed=embed)

    @command(
        "music (?:play|queue) (.+)",
        permission_name="music.queue",
        global_command=True,
        description="Queues a URL for playback."
    )
    async def play(self, message, args):
        player = await self.get_player(message.server, message.author)
        url = args[0].strip()

        if url.startswith("prepend:"):
            url = url.lstrip("prepend:")
            prepend = True
        else:
            prepend = False

        info = await self.downloader.extract_info(player.playlist.loop, url, download=False, process=False)

        if not info:
            embed = discord.Embed(
                title="Unable to play URL",
                colour=discord.Colour.red(),
                description="This URL could not be played."
            )
            return Message(embed=embed)

        if info.get("url", "").startswith("ytsearch"):
            info = await self.downloader.extract_info(
                player.playlist.loop,
                url,
                download=False,
                process=True,
                on_error=lambda e: asyncio.ensure_future(
                    self.send_message(channel, "```\n%s\n```" % e), loop=self.loop)
            )

            if not info.get("entries", []):
                raise CommandError(f"No videos were found.")

            song_url = info["entries"][0]["webpage_url"]
            return await self.play._func(self, message, [song_url])

        if "entries" in info:
            num_songs = sum(1 for _ in info["entries"])

            if info['extractor'].lower() in ['youtube:playlist', 'soundcloud:set', 'bandcamp:album']:
                return await self.play_playlist_async(player, message.channel, message.author, url, info["extractor"])

            t0 = time.time()

            # My test was 1.2 seconds per song, but we maybe should fudge it a bit, unless we can
            # monitor it and edit the message with the estimated time, but that's some ADVANCED SHIT
            # I don't think we can hook into it anyways, so this will have to do.
            # It would probably be a thread to check a few playlists and get the speed from that
            # Different playlists might download at different speeds though
            wait_per_song = 1.2

            procmesg = await self.bot.send_message(
                channel,
                'Gathering playlist information for {} songs{}'.format(
                    num_songs,
                    ', ETA: {} seconds'.format(
                        self._fixg(
                            num_songs * wait_per_song
                        )
                    ) if num_songs >= 10 else '.'
                )
            )

            entry_list, position = await player.playlist.import_from(url, channel=channel, author=author)

            tnow = time.time()
            ttime = tnow - t0
            listlen = len(entry_list)

            log.info("Processed {} songs in {} seconds at {:.2f}s/song, {:+.2g}/song from expected ({}s)".format(
                listlen,
                self._fixg(ttime),
                ttime / listlen,
                ttime / listlen - wait_per_song,
                self._fixg(wait_per_song * num_songs))
            )

            await self.bot.delete_message(procmesg)

            embed_description = f"**{(listlen)}** songs have been queued!"
        else:
            entry, position = await player.playlist.add_entry(url, channel=message.channel, author=message.author, prepend=prepend)
            embed_description = f"**{entry.title}** has been queued!"

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Music",
            description=embed_description
        ).add_field(
            name="Queue position",
            value="Up next!" if (position == 1 and player.is_stopped) else position
        )



        if not (position == 1 and player.is_stopped):
            embed.add_field(
                name="Time remaining",
                value=await player.playlist.estimate_time_until(position, player)
            )

        return Message(embed=embed)

    @command(
        patterns=[
            "music shuffle$",
            "music shuffle (.+)"
        ],
        permission_name="music.shuffle",
        global_command=True,
        description="Shuffles the music queue."
    )
    async def shuffle(self, channel, args):
        player = await self.get_player(message.server, message.author)

        if args:
            player.playlist.shuffle(args[0])
        else:
            player.playlist.shuffle()

        return Message("Playlist shuffled!")

    @command(
        patterns=[
            "music seek$",
            "music seek (.+)"
        ],
        permission_name="music.seek",
        global_command=True,
        description="Seeks the current song."
    )
    async def seek(self, message, args):
        player = await self.get_player(message.server, message.author)

        if player.is_stopped:
            raise CommandError("Can't seek! The player is not playing!")

        try:
            seek = args[0]
        except IndexError:
            raise CommandError('A time is required to seek.')

        if not (
            message.author == player.current_entry.meta.get("author", None)
            or message.author.server_permissions.administrator
        ):
            return Message("no!")

        try:
            original_seek = seek

            seek = pytimeparse.parse(seek)

            if not seek:
                seek = int(original_seek)

            if seek < 0:
                raise ValueError()
        except (TypeError, ValueError):
            raise CommandError('The time you have given is invalid.')

        try:
            player.seek(seek)
        except ValueError as e:
            raise CommandError(str(e))

        return Message('Seeked video to %s!' % (
            str(timedelta(seconds=seek)).lstrip('0').lstrip(':')
        ))

    @command(
        patterns=[
            "music skip",
        ],
        permission_name="music.skip",
        global_command=True,
        description="Skips the current playing song."
    )
    async def skip(self, message, args):
        player = await self.get_player(message.server, message.author)

        if player.is_stopped:
            raise CommandError("You cannot skip when there are no songs playing!")

        if not player.current_entry:
            if player.playlist.peek():
                return Message("The next song (%s) is downloading, please wait." % player.playlist.peek().title)

        if (
            message.author == player.current_entry.meta.get("author", None)
            or message.author.server_permissions.administrator
        ):
            player.skip()
            return Message("Skipped! (instantly)")

        return Message("no!")

    @command(
        "music summon$",
        permission_name="music.summon",
        description="Summons the bot to a channel"
    )
    async def summon(self, author):
        voice_client = await self.get_voice_client(author.server, author)

        if author.voice_channel and (voice_client.channel != author.voice_channel):
            perms = author.voice_channel.permissions_for(author.voice_channel.server.me)

            if not perms.connect:
                raise CommandError(f"I do not have permissions to connect to \"{sanitize(author.voice_channel.name)}\"!")
            elif not perms.speak:
                raise CommandError(f"I do not have permissions to speak in \"{sanitize(author.voice_channel.name)}\"!")

            await voice_client.move_to(author.voice_channel)

        return Message("Bot summoned!")

    # Discord events

    async def on_logout(self):
        log.info("Got logout event!")
        await self.disconnect_all_voice_clients()

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

    # Music helper functions

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
            if not caller:
                return

            voice_client = await self.get_voice_client(server, caller)

            playlist = Playlist(self, server)
            player = Player(self, playlist, voice_client)\
                .on("play", self.on_player_play)
            self.players[server.id] = player

            return player

    async def play_playlist_async(self, player, channel, author, playlist_url, extractor_type):
        info = await self.downloader.extract_info(player.playlist.loop, playlist_url, download=False, process=False)

        if not info:
            raise exceptions.CommandError("That playlist cannot be played.")

        num_songs = sum(1 for _ in info['entries'])
        t0 = time.time()

        busymsg = await self.bot.send_message(channel, "Processing %s songs..." % num_songs)

        entries_added = 0
        if extractor_type == 'youtube:playlist':
            try:
                entries_added = await player.playlist.async_process_youtube_playlist(
                    playlist_url, channel=channel, author=author)
                # TODO: Add hook to be called after each song
                # TODO: Add permissions

            except Exception:
                traceback.print_exc()
                raise CommandError('Error handling playlist %s queuing.' % playlist_url)

        elif extractor_type.lower() in ['soundcloud:set', 'bandcamp:album']:
            try:
                entries_added = await player.playlist.async_process_sc_bc_playlist(
                    playlist_url, channel=channel, author=author)
                # TODO: Add hook to be called after each song
                # TODO: Add permissions

            except Exception:
                traceback.print_exc()
                raise CommandError('Error handling playlist %s queuing.' % playlist_url)


        songs_processed = len(entries_added)

        await self.bot.delete_message(busymsg)

        songs_added = len(entries_added)
        tnow = time.time()
        ttime = tnow - t0
        wait_per_song = 1.2
        # TODO: actually calculate wait per song in the process function and return that too

        # This is technically inaccurate since bad songs are ignored but still take up time
        log.info("Processed {}/{} songs in {} seconds at {:.2f}s/song, {:+.2g}/song from expected ({}s)".format(
            songs_processed,
            num_songs,
            self._fixg(ttime),
            ttime / num_songs,
            ttime / num_songs - wait_per_song,
            self._fixg(wait_per_song * num_songs))
        )

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Music",
            description="Enqueued {} songs to be played in {} seconds".format(
                songs_added,
                self._fixg(ttime, 1)
            )
        )

        return Message(embed=embed)

    async def disconnect_all_voice_clients(self):
        for player in self.players.values():
            player.kill()
            await player.voice_client.disconnect()

    @staticmethod
    def _fixg(x, dp=2):
        return ('{:.%sf}' % dp).format(x).rstrip('0').rstrip('.')

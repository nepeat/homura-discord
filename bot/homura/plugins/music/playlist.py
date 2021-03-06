# coding=utf-8
import datetime
import logging
import os
import random
import traceback
from collections import deque
from itertools import islice
from urllib.error import URLError

import discord
from youtube_dl.utils import DownloadError, UnsupportedError

from homura.lib.eventemitter import EventEmitter
from homura.lib.util import get_header
from homura.plugins.music.exceptions import ExtractionError, WrongEntryTypeError
from homura.plugins.music.objects import StreamPlaylistEntry, URLPlaylistEntry

DISCORD_FIELD_CHAR_LIMIT = 1000
log = logging.getLogger(__name__)


class Playlist(EventEmitter):
    def __init__(self, plugin, guild):
        super().__init__()

        self.plugin = plugin
        self.bot = plugin.bot
        self.loop = plugin.bot.loop
        self.redis = plugin.bot.redis
        self.downloader = plugin.downloader
        self.guild = guild
        self.entries = deque()

        self.queue_key = "music:queue:%s" % (self.guild.id)

        self.loop.create_task(self.load_saved())

    def __iter__(self):
        return iter(self.entries)

    async def load_saved(self):
        queue = await self.redis.lrange(self.queue_key, 0, -1)

        for blob in await queue.aslist():
            if "StreamPlaylistEntry" in blob:
                entry = StreamPlaylistEntry.from_json(self, blob)
            else:
                entry = URLPlaylistEntry.from_json(self, blob)

            self._add_entry(entry, saved=True)

    def shuffle(self, seed: str=None):
        """
            Shuffles the queue.
            :param seed: A seed to shuffle the queue with.
        """
        if seed:
            random.seed(seed)

        random.shuffle(self.entries)
        self.loop.create_task(self.refresh_saved_queue())
        random.seed()

    def clear(self, kill=False, last_entry=None):
        """
            Clears the queue.
        """
        self.entries.clear()

        if kill and last_entry:
            self.loop.create_task(self.redis.lpush(self.queue_key, [last_entry.to_json()]))
        else:
            self.loop.create_task(self.redis.delete([self.queue_key]))

    async def add_entry(self, song_url, prepend=False, stream=False, **meta):
        """
            Validates and adds a song_url to be played. This does not start the download of the song.
            Returns the entry & the position it is in the queue.
            :param song_url: The song url to add to the playlist.
            :param prepend: Prepends the song to the playlist.
            :param meta: Any additional metadata to add to the playlist entry.
        """

        try:
            info = await self.downloader.extract_info(self.loop, song_url, download=False)
        except Exception as e:
            raise ExtractionError("Could not extract information from {}\n\n{}".format(song_url, e))

        if not info:
            raise ExtractionError("Could not extract information from %s" % song_url)

        # TODO: Sort out what happens next when this happens
        if info.get("_type", None) == "playlist":
            raise WrongEntryTypeError("This is a playlist.", True, info.get("webpage_url", None) or info.get("url", None))

        if info.get('is_live', False) or stream:
            return await self.add_stream_entry(song_url, info=info, prepend=prepend, **meta)

        if info["extractor"] in ["generic", "Dropbox"]:
            try:
                content_type = await get_header(self.plugin.bot.aiosession, info["url"], "CONTENT-TYPE")
                log.warning("Got content type %s", content_type)

            except Exception as e:
                log.warning("Failed to get content type for url %s (%s)", song_url, e)
                content_type = None

            if content_type:
                if content_type.startswith(("application/", "image/")):
                    if "/ogg" not in content_type:  # How does a server say `application/ogg` what the actual fuck
                        raise ExtractionError("Invalid content type \"%s\" for url %s" % (content_type, song_url))
                elif content_type.startswith('text/html') and info['extractor'] == 'generic':
                    log.warning("Got text/html for content-type, this might be a stream.")
                    return await self.add_stream_entry(song_url, info=info, **meta)  # TODO: Check for shoutcast/icecast
                elif not content_type.startswith(("audio/", "video/")):
                    log.warning("Questionable content type \"%s\" for url %s", content_type, song_url)

        entry = URLPlaylistEntry(
            self,
            song_url,
            info.get("title", "Untitled"),
            info.get("duration", 0) or 0,
            self.downloader.ytdl.prepare_filename(info),
            **meta
        )
        self._add_entry(entry, prepend=prepend)
        
        if prepend:
            position = 1
        else:
            position = len(self.entries)

        return entry, position

    async def add_stream_entry(self, song_url, info=None, prepend=False, **meta):
        if info is None:
            info = {'title': song_url, 'extractor': None}

            try:
                info = await self.downloader.extract_info(self.loop, song_url, download=False)

            except DownloadError as e:
                if e.exc_info[0] == UnsupportedError:  # ytdl doesn't like it but its probably a stream
                    log.debug("Assuming content is a direct stream")

                elif e.exc_info[0] == URLError:
                    if os.path.exists(os.path.abspath(song_url)):
                        raise ExtractionError("This is not a stream, this is a file path.")

                    else:  # it might be a file path that just doesn't exist
                        raise ExtractionError("Invalid input: {0.exc_info[0]}: {0.exc_info[1].reason}".format(e))

                else:
                    # traceback.print_exc()
                    raise ExtractionError("Unknown error: {}".format(e))

            except Exception as e:
                log.error('Could not extract information from {} ({}), falling back to direct'.format(song_url, e), exc_info=True)

        dest_url = song_url
        if "formats" in info:
            dest_url = info["formats"][0].get("url", dest_url)

        if info.get('extractor', "generic") != "generic":
            dest_url = info.get('url', dest_url)

        if info.get('extractor', None) == 'twitch:stream':  # may need to add other twitch types
            title = info.get('description')
        else:
            title = info.get('title', 'Untitled')

        # TODO: A bit more validation, "~stream some_url" should not just say :ok_hand:

        entry = StreamPlaylistEntry(
            self,
            song_url,
            title,
            destination=dest_url,
            **meta
        )
        self._add_entry(entry, prepend=prepend)

        if prepend:
            position = 1
        else:
            position = len(self.entries)

        return entry, position

    def _add_entry(self, entry, saved=False, prepend=False):
        if prepend:
            self.entries.appendleft(entry)
        else:
            self.entries.append(entry)

        if not saved:
            self.loop.create_task(self.save_entry(entry, prepend))

        self.emit("entry-added", playlist=self, entry=entry)

        if self.peek() is entry:
            entry.get_ready_future()

    async def save_entry(self, entry, prepend=False):
        await self.redis.hincrby("music:played", entry.url, 1)
        self.bot.stats.count("music_play", url=entry.url)

        if prepend:
            await self.redis.lpush(self.queue_key, [entry.to_json()])
        else:
            await self.redis.rpush(self.queue_key, [entry.to_json()])

    async def refresh_saved_queue(self):
        await self.redis.delete([self.queue_key])
        await self.redis.rpush(self.queue_key, [entry.to_json() for entry in self.entries])

    async def import_from(self, playlist_url, **meta):
        """
            Imports the songs from `playlist_url` and queues them to be played.
            Returns a list of `entries` that have been enqueued.
            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
            :param meta: Any additional metadata to add to the playlist entry
        """
        position = len(self.entries) + 1
        entry_list = []

        try:
            info = await self.downloader.extract_info(self.loop, playlist_url, download=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(playlist_url, e))

        if not info:
            raise ExtractionError('Could not extract information from %s' % playlist_url)

        # Once again, the generic extractor fucks things up.
        if info.get('extractor', None) == 'generic':
            url_field = 'url'
        else:
            url_field = 'webpage_url'

        baditems = 0
        for items in info['entries']:
            if items:
                try:
                    entry = URLPlaylistEntry(
                        self,
                        items[url_field],
                        items.get('title', 'Untitled'),
                        items.get('duration', 0) or 0,
                        self.downloader.ytdl.prepare_filename(items),
                        **meta
                    )

                    self._add_entry(entry)
                    entry_list.append(entry)
                except:
                    baditems += 1
                    # Once I know more about what's happening here I can add a proper message
                    log.error(traceback.format_exc())
                    log.error(items)
                    log.error("Could not add item")
            else:
                baditems += 1

        if baditems:
            log.debug("Skipped %s bad entries", baditems)

        return entry_list, position

    async def async_process_playlist(self, playlist_url, extractor, **meta):
        """
            Processes youtube playlists, soundcloud set and bancdamp album links from `playlist_url` in a questionable,
            async fashion.
            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
            :param extractor: The extractor to be using for the playlist url
            :param meta: Any additional metadata to add to the playlist entry
        """
        try:
            info = await self.downloader.extract_info(self.loop, playlist_url, download=False, process=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(playlist_url, e))

        if not info:
            raise ExtractionError('Could not extract information from %s' % playlist_url)

        gooditems = []
        baditems = 0
        for entry_data in info["entries"]:
            if entry_data:
                if extractor == "youtube:playlist":
                    baseurl = info['webpage_url'].split('playlist?list=')[0]
                    song_url = baseurl + 'watch?v=%s' % entry_data['id']
                elif extractor in ['soundcloud:set', 'bandcamp:album']:
                    song_url = entry_data['url']
                else:
                    raise ExtractionError("No handler for extractor %s" % extractor)

                try:
                    entry, elen = await self.add_entry(song_url, **meta)
                    gooditems.append(entry)
                except ExtractionError:
                    baditems += 1
                except Exception as e:
                    baditems += 1
                    log.warning("There was an error adding the song {}: {}: {}\n".format(
                        entry_data['id'], e.__class__.__name__, e))
            else:
                baditems += 1

        if baditems:
            log.debug("Skipped %s bad entries" % baditems)

        return gooditems

    async def get_next_entry(self, predownload_next=True):
        """
            A coroutine which will return the next song or None if no songs left to play.

            Additionally, if predownload_next is set to True, it will attempt to download the next
            song to be played - so that it's ready by the time we get to it.
        """
        if not self.entries:
            return None

        entry = self.entries.popleft()
        await self.redis.lpop(self.queue_key)

        if predownload_next:
            next_entry = self.peek()
            if next_entry:
                next_entry.get_ready_future()

        try:
            return await entry.get_ready_future()
        except ExtractionError:
            return await self.get_next_entry()

    def peek(self):
        """
            Returns the next entry that should be scheduled to be played.
        """
        if self.entries:
            return self.entries[0]

    async def estimate_time_until(self, position, player):
        """
            (very) Roughly estimates the time till the queue will 'position'
        """
        estimated_time = sum([e.duration for e in islice(self.entries, position - 1)])

        # When the player plays a song, it eats the first playlist item, so we just have to add the time back
        if not player.is_stopped and player.current_entry:
            estimated_time += player.current_entry.duration - player.progress

        return datetime.timedelta(seconds=estimated_time)

    def format_discord(self, max_length=DISCORD_FIELD_CHAR_LIMIT, formatted=True):
        queue_lines = []
        queue_unlisted = 0
        if formatted:
            andmoretext = '* ... and %s more*' % ('x' * len(self.entries))
        else:
            andmoretext = '... and %s more' % ('x' * len(self.entries))

        for i, item in enumerate(self, 1):
            if item.meta.get("author", ""):
                if formatted:
                    nextline = f"{i}. **{item.title}** added by {item.meta['author'].mention}".strip()
                else:
                    nextline = f"{i}. {item.title} added by {item.meta['author'].name}".strip()
            else:
                if formatted:
                    nextline = f"{i}. **{item.title}**".strip()
                else:
                    nextline = f"{i}. {item.title}".strip()

            currentlinesum = sum(len(x) + 1 for x in queue_lines)

            if max_length and (currentlinesum + len(nextline) + len(andmoretext) > max_length):
                if currentlinesum + len(andmoretext):
                    queue_unlisted += 1
                    continue

            queue_lines.append(nextline)

        if queue_unlisted:
            queue_lines.append("\n*... and %s more*" % queue_unlisted)

        if not queue_lines:
            queue_lines.append("There are no songs queued! Queue something with !music play.")

        return "\n".join(queue_lines)

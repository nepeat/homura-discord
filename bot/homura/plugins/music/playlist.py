import datetime
import logging
import random
from collections import deque
from itertools import islice
import traceback
import functools

from homura.plugins.music.exceptions import ExtractionError, WrongEntryTypeError
from homura.plugins.music.objects import EventEmitter, URLPlaylistEntry

log = logging.getLogger(__name__)


class Playlist(EventEmitter):
    def __init__(self, plugin, server):
        super().__init__()

        self.plugin = plugin
        self.bot = plugin.bot
        self.loop = plugin.bot.loop
        self.redis = plugin.bot.redis
        self.downloader = plugin.downloader
        self.server = server
        self.entries = deque()

        self.loop.create_task(self.load_saved())

    def __iter__(self):
        return iter(self.entries)

    async def load_saved(self):
        queue = await self.redis.lrange("music:queue:" + self.server.id, 0, -1)

        for blob in await queue.aslist():
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
        self.loop.create_task(self.refresh_saved_queue)
        random.seed()

    def clear(self, kill=False, last_entry=None):
        """
            Clears the queue.
        """
        self.entries.clear()

        redis_key = "music:queue:" + self.server.id
        if kill and last_entry:
            self.loop.create_task(self.redis.lpush(redis_key, [last_entry.to_json()]))
        else:
            self.loop.create_task(self.redis.delete([redis_key]))

    async def add_entry(self, song_url, prepend=False, **meta):
        """
            Validates and adds a song_url to be played. This does not start the download of the song.
            Returns the entry & the position it is in the queue.
            :param song_url: The song url to add to the playlist.
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

        if info["extractor"] in ["generic", "Dropbox"]:
            try:
                content_type = await get_header(self.plugin.bot.aiosession, info["url"], "CONTENT-TYPE")
                log.warning("Got content type", content_type)

            except Exception as e:
                log.warning("Failed to get content type for url %s (%s)", song_url, e)
                content_type = None

            if content_type:
                if content_type.startswith(("application/", "image/")):
                    if "/ogg" not in content_type:  # How does a server say `application/ogg` what the actual fuck
                        raise ExtractionError("Invalid content type \"%s\" for url %s" % (content_type, song_url))

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
        self._add_entry(entry, saved=False, prepend=prepend)
        return entry, len(self.entries)

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
        redis_key = "music:queue:" + self.server.id

        await self.redis.hincrby("music:played", entry.url, 1)

        if prepend:
            await self.redis.lpush(redis_key, [entry.to_json()])
        else:
            await self.redis.rpush(redis_key, [entry.to_json()])

    async def refresh_saved_queue(self):
        await self.redis.delete(["music:queue:" + self.server.id])
        await self.redis.rpush("music:queue:" + self.server.id, *[entry.to_json() for entry in self.entries])

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

    async def async_process_youtube_playlist(self, playlist_url, **meta):
        """
            Processes youtube playlists links from `playlist_url` in a questionable, async fashion.
            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
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
        for entry_data in info['entries']:
            if entry_data:
                baseurl = info['webpage_url'].split('playlist?list=')[0]
                song_url = baseurl + 'watch?v=%s' % entry_data['id']

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

    async def async_process_sc_bc_playlist(self, playlist_url, **meta):
        """
            Processes soundcloud set and bancdamp album links from `playlist_url` in a questionable, async fashion.
            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
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
        for entry_data in info['entries']:
            if entry_data:
                song_url = entry_data['url']

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
        await self.redis.lpop("music:queue:" + self.server.id)

        if predownload_next:
            next_entry = self.peek()
            if next_entry:
                next_entry.get_ready_future()

        return await entry.get_ready_future()

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

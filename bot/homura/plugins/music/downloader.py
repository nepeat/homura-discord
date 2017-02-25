import hashlib
import functools
import json
import os
from concurrent.futures import ThreadPoolExecutor

import youtube_dl

YOUTUBEDL_ARGS = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audioformat": "mp3",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"
}

ONE_DAY_IN_SECONDS = 60 * 60 * 24

youtube_dl.utils.bug_reports_message = lambda: ""

class Downloader(object):
    def __init__(self, bot, download_folder=None):
        self.bot = bot
        self.download_folder = download_folder
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    @property
    def ytdl(self):
        ytdl = youtube_dl.YoutubeDL(YOUTUBEDL_ARGS)

        if self.download_folder:
            otmpl = ytdl.params["outtmpl"]
            ytdl.params["outtmpl"] = os.path.join(self.download_folder, otmpl)

        return ytdl

    def hash_string(self, data):
        if isinstance(data, str):
            data = data.encode("utf8")

        m = hashlib.md5()
        m.update(data)
        return m.hexdigest()

    async def set_cache(self, url, data, **kwargs):
        cachekey = "musicbot:cache:" + self.hash_string(url)

        # Do not cache searches on YouTube.
        if "url" in data and data["url"].startswith("ytsearch"):
            return None

        if "process" in kwargs and kwargs["process"] is True:
            cachekey += ":processed"

        try:
            await self.bot.redis.setex(cachekey, ONE_DAY_IN_SECONDS, json.dumps(data))
        except TypeError:
            pass

    async def get_cache(self, url, **kwargs):
        cachekey = "musicbot:cache:" + self.hash_string(url)

        # Don't hit the cache if we are downloading the video.
        if "download" in kwargs and kwargs["download"] is True:
            return None

        if "process" in kwargs and kwargs["process"] is True:
            cachekey += ":processed"

        try:
            _data = await self.bot.redis.get(cachekey)

            if not _data:
                return

            data = json.loads(_data)
            if data:
                return data
        except json.JSONDecodeError:
            return None

    async def extract_info(self, loop, *args, on_error=None, **kwargs):
        """
            Runs ytdl.extract_info within the threadpool. Returns a future that will fire when it's done.
            If `on_error` is passed and an exception is raised, the exception will be caught and passed to
            on_error as an argument.
        """

        info = await self.get_cache(args[0], **kwargs)
        if info:
            return info

        try:
            info = await loop.run_in_executor(self.thread_pool, functools.partial(self.ytdl.extract_info, *args, **kwargs))
            await self.set_cache(args[0], info, **kwargs)
            return info
        except Exception as e:
            if callable(on_error):
                # (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError)
                # I hope I don't have to deal with ContentTooShortError's
                if asyncio.iscoroutinefunction(on_error):
                    asyncio.ensure_future(on_error(e), loop=loop)
                elif asyncio.iscoroutine(on_error):
                    asyncio.ensure_future(on_error, loop=loop)
                else:
                    loop.call_soon_threadsafe(on_error, e)

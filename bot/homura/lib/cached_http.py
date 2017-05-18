# coding=utf-8
import json
import urllib.parse

from homura.lib.util import md5_string

USER_AGENT = "github.com/nepeat/homura-discord | nepeat#6071 | This is discord bot. This is mistake."

class CachedHTTPException(Exception):
    pass


class CachedHTTP(object):
    def __init__(self, bot, default_cache_time: int=300):
        self.bot = bot
        # 60 seconds * 5 minutes = 300 seconds
        self.cache_time = default_cache_time

    @staticmethod
    def generate_cachekey(url: str, params: dict, **kwargs) -> str:
        """
        Generates a cache key for Redis storage.

        :param url: URL for the base portion of the key.
        :param params: Request parameters that will be hashed into the key.
        :param kwargs: `json` is the only argument that modifies the key.
        """
        pieces = urllib.parse.urlparse(url)
        cache_key = pieces.netloc + ":" + md5_string(pieces.path)

        if kwargs.get("json", True):
            cache_key += ":json"

        cache_extra = ":".join([str(x) + ":" + str(y) for x, y in params.items()])
        if cache_extra:
            cache_key += md5_string(cache_extra)

        return cache_key

    async def get(self, url: str, params: dict=None, headers: dict=None, asjson: bool=False, **kwargs):
        """
        Extremely simplified cached GET for external APIs.

        :param url: URL of the external API
        :param params: URL parameters for the API
        :param headers: Additional headers to be sent to the API.
        :param asjson: Returns JSON
        :param kwargs: `json` is the only argument, that returns the response as JSON.
        """
        if not params:
            params = {}

        cache_key = self.generate_cachekey(url, params, json=asjson)
        cache_data = await self.bot.redis.get(cache_key)
        cache_time = kwargs.get("cache_time", self.cache_time)

        if cache_data:
            return json.loads(cache_data)

        if not headers:
            headers = {
                "User-Agent": USER_AGENT
            }

        async with self.bot.aiosession.get(
            url=url,
            params=params,
            headers=headers
        ) as response:
            if asjson:
                reply = await response.json()
            else:
                reply = await response.text()

        if response.status == 429:
            raise CachedHTTPException("We are rate limited.")

        await self.bot.redis.setex(cache_key, cache_time, json.dumps(reply))
        return reply

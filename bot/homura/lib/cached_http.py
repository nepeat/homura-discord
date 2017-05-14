from aiohttp import ClientSession
from asyncio_redis import Connection

import hashlib
import urllib.parse
from homura.util import md5_string
import json

CACHE_TIME = 60 * 5 # 5 minutes
USER_AGENT = "github.com/nepeat/homura-discord | nepeat#6071 | This is discord bot. This is mistake."


class CachedHTTP(object):
    def __init__(self, bot):
        self.bot = bot

    def generate_cachekey(self, url: str, params: dict):
        pieces = urllib.parse.urlparse(url)
        cache_key = pieces.netloc + ":" + md5_string(pieces.path)

        cache_extra = ":".join([str(x) + ":" + str(y) for x, y  in params.items()])
        if cache_extra:
            cache_key += md5_string(cache_extra)

        return cache_key

    async def get(self, url, params={}, headers=None, asjson=False):
        cache_key = self.generate_cachekey(url, params)
        cache_data = await self.bot.redis.get(cache_key)

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


        await self.bot.redis.setex(cache_key, CACHE_TIME, json.dumps(reply))
        return reply

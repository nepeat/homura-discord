import time

import asyncio
import pytest
from homura.lib.cached_http import CachedHTTP

from .. import slow


@pytest.mark.asyncio
@slow
async def test_cached_get_plain_json(bot):
    bot = await bot
    http = CachedHTTP(bot)

    text1 = await http.get("http://date.jsontest.com/?test=text", cache_time=1)
    text2 = await http.get("http://date.jsontest.com/?test=text", cache_time=1)
    assert text1 == text2

    json1 = await http.get("http://date.jsontest.com/?test=json", cache_time=1, asjson=True)
    json2 = await http.get("http://date.jsontest.com/?test=json", cache_time=1, asjson=True)
    assert json1 == json2


@pytest.mark.asyncio
@slow
async def test_broken_cache_get_plain_json(bot):
    bot = await bot
    http = CachedHTTP(bot)

    text1 = await http.get("http://date.jsontest.com/?test=expire", cache_time=1)
    await asyncio.sleep(1.1)
    text2 = await http.get("http://date.jsontest.com/?test=expire", cache_time=2)
    assert text1 != text2

    json1 = await http.get("http://date.jsontest.com/?test=expire", cache_time=1, asjson=True)
    await asyncio.sleep(1.1)
    json2 = await http.get("http://date.jsontest.com/?test=expire", cache_time=2, asjson=True)
    assert json1 != json2


@pytest.mark.asyncio
@slow
async def test_cached_get_params_plain_json(bot):
    bot = await bot
    http = CachedHTTP(bot)

    cached_text = f"cached_text:{time.time()}"
    text1 = await http.get("http://md5.jsontest.com", params={"text": cached_text}, cache_time=1)
    text2 = await http.get("http://md5.jsontest.com", params={"text": cached_text}, cache_time=1)
    assert text1 == text2

    cached_json = f"cached_json:{time.time()}"
    json1 = await http.get("http://md5.jsontest.com", params={"text": cached_json}, cache_time=1, asjson=True)
    json2 = await http.get("http://md5.jsontest.com", params={"text": cached_json}, cache_time=1, asjson=True)
    assert json1 == json2

# coding=utf-8
import re

import aiohttp
from homura.plugins.antispam.signals import Delete

url_regex = re.compile(r"(https?://\S+)")


async def validate_url(session, url):
    with aiohttp.Timeout(10):
        try:
            async with session.get(url) as response:
                if response.headers:
                    return True

                return False
        except aiohttp.ClientError:
            return False


async def check(session, message):
    content = message.content.lower()
    urls = url_regex.search(content)

    if message.attachments:
        return
    elif urls:
        for url in urls.groups():
            if not await validate_url(session, url):
                raise Delete("quiet")
    else:
        raise Delete("quiet")

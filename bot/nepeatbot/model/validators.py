import re

import aiohttp

url_regex = re.compile(r"(https?:\/\/\S+)")

async def validate_url(session, url):
    with aiohttp.Timeout(10):
        try:
            async with session.get(url) as response:
                if response.headers:
                    return True

                return False
        except aiohttp.errors.ClientError:
            return False

# coding=utf-8
import aiohttp
import os
import logging
import re

from homura.plugins.antispam.signals import Delete

log = logging.getLogger(__name__)
url_regex = re.compile(r"(https?://\S+)")
NSFWAPI_URL = os.environ.get("NSFWAPI_URL", "http://localhost:5001")


async def check(session, message):
    for embed in message.embeds:
        if "thumbnail" not in embed:
            continue

        if "proxy_url" not in embed["thumbnail"]:
            continue

        response = await test_image(session, embed["thumbnail"]["proxy_url"])
        if response.get("nsfw", False):
            raise Delete()

    urls = url_regex.search(message.content)
    if urls:
        for url in urls.groups():
            response = await test_image(session, url)
            if response.get("nsfw", False):
                raise Delete

async def test_image(session, image_url, **kwargs) -> dict:
    params = {
        "url": image_url,
    }

    if kwargs:
        params.update(kwargs)

    log.debug(params)

    try:
        async with session.get(
            url=NSFWAPI_URL + "/check",
            params=params
        ) as response:
            try:
                reply = await response.json()
                if reply.get("error"):
                    log.error("Error pushing event to server.")
                    log.error(reply)
                    return {}
                return reply
            except ValueError:
                log.error("Error parsing JSON.")
                log.error(await response.text())
                pass
    except aiohttp.errors.ClientError:
        pass

    return {}

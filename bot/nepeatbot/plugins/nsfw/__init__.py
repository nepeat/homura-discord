import datetime
import logging
import random
import xml.etree.ElementTree as ET

import aiohttp
import discord

from nepeatbot.plugins.common import Message, PluginBase, command
from nepeatbot.util import sanitize

log = logging.getLogger(__name__)

API_ENDPOINTS = {
    "gelbooru": [
        "https://rule34.xxx/index.php",
        "https://gelbooru.com/index.php"
    ]
}
USER_AGENT = "github.com/nepeat/nepeatbot | nepeat#6071 | This is discord bot. This is mistake."

class NSFWPlugin(PluginBase):
    @command("rule34 (.+)", permission_name="nsfw.rule34")
    async def rule34(self, channel, args):
        image = await self.get_randombooru(args[0].strip())
        if not image:
            return Message(
                f"No posts tagged `{sanitize(args[0])}` were found.",
                reply=True
            )

        return Message(embed=self.create_image_embed(
            url=image["url"],
            bottom_text=f"Tagged {image['tags'].strip().replace(' ', ', ')}"
        ))

    async def get_randombooru(self, tags: str):
        backend = random.choice(list(API_ENDPOINTS.keys()))
        endpoint = random.choice(API_ENDPOINTS[backend])

        if backend == "gelbooru":
            return await self.get_gelbooru(endpoint, tags)

    async def get_gelbooru(self, endpoint, tags, nsfw=True):
        if nsfw:
            tags = tags + " -rating:safe"

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags
        }

        async with self.bot.aiosession.get(
            url=endpoint,
            params=params,
            headers={
                "User-Agent": USER_AGENT
            }
        ) as response:
            reply = await response.text()

        root = ET.fromstring(reply)
        images = root.findall("post")

        if not images:
            return None

        image = random.choice(images)

        url = image.get("file_url")
        if url.startswith("//"):
            url = "https://" + url[2:]

        return dict(
            url=url.replace("http:", "https:"),
            rating=image.get("rating") or None,
            tags=image.get("tags") or []
        )

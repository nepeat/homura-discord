import logging
import random

from nepeatbot.plugins.common import Message, PluginBase, command
from nepeatbot.plugins.nsfw.common import API_ENDPOINTS, USER_AGENT
from nepeatbot.plugins.nsfw.fetcher import ImageFetcher
from nepeatbot.util import sanitize

log = logging.getLogger(__name__)


class NSFWPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetcher = ImageFetcher(self.bot.aiosession)

    @command("nsfw (.+)", permission_name="nsfw.rule34")
    async def rule34(self, channel, args):
        image = await self.get_randombooru(args[0].strip())
        if not image:
            return Message(
                f"No posts tagged `{sanitize(args[0])}` were found.",
                reply=True
            )

        return Message(embed=self.create_image_embed(
            top_text=image["friendly_name"],
            top_url=image["permalink"],
            url=image["url"],
            bottom_text=f"Tagged {image['tags'].strip().replace(' ', ', ')}"
        ))

    async def get_randombooru(self, tags: str):
        image = None
        backend = random.choice(list(API_ENDPOINTS.keys()))

        sites = list(API_ENDPOINTS[backend])
        while sites:
            site = random.choice(sites)
            sites.remove(site)
            if backend == "gelbooru":
                image = await self.fetcher.gelbooru(site, tags)
            elif backend == "danbooru":
                image = await self.fetcher.danbooru(site, tags)

            if isinstance(image, dict):
                return image

        return None

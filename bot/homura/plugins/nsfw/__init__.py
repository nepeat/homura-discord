# coding=utf-8
import logging

from homura.apis.nsfw import ImageFetcher
from homura.lib.cached_http import CachedHTTP
from homura.lib.structure import CommandError, Message
from homura.lib.util import sanitize
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class NSFWPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetcher = ImageFetcher(CachedHTTP(self.bot))

    @command(
        "nsfw (.+)",
        permission_name="nsfw.rule34",
        description="Fetches an image from gelbooru, rule34, and e621.",
        usage="nsfw <query>"
    )
    async def rule34(self, args):
        image = await self.fetcher.random(args[0].strip())

        if not image:
            raise CommandError(f"No posts tagged '{sanitize(args[0])}' were found.")

        return Message(embed=self.create_image_embed(
            top_text=image["friendly_name"],
            top_url=image["permalink"],
            url=image["url"],
            bottom_text=f"Tagged {image['tags'].strip().replace(' ', ', ')}"
        ))

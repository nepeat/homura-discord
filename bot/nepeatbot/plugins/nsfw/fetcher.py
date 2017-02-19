import logging
import random
import xml.etree.ElementTree as ET

from nepeatbot.plugins.nsfw.common import USER_AGENT

log = logging.getLogger(__name__)

class ImageFetcher(object):
    def __init__(self, aiosession):
        self.aiosession = aiosession

    def dict_return(self, site, image):
        url = image.get("file_url")
        if url.startswith("//"):
            url = "https://" + url[2:]

        return dict(
            id=image.get("id") or None,
            url=url.replace("http:", "https:"),
            rating=image.get("rating") or None,
            tags=image.get("tags") or [],
            friendly_name=site["friendly_name"],
            permalink=site["permalink"].format(image.get("id") or None)
        )

    def safe_shuffle(self, images):
        for x in range(0, 10):
            image = random.choice(images)
            if not image.get("url").endswith(".webm"):
                return image

    async def gelbooru(self, site, tags, nsfw=True):
        if nsfw:
            tags = tags + " -rating:safe"

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags
        }

        async with self.aiosession.get(
            url=site["endpoint"],
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

        image = self.safe_shuffle(images)

        return self.dict_return(site, image)

    async def danbooru(self, site, tags, nsfw=True):
        if nsfw:
            tags = tags + " -rating:safe"

        params = {
            "tags": tags
        }

        async with self.aiosession.get(
            url=site["endpoint"],
            params=params,
            headers={
                "User-Agent": USER_AGENT
            }
        ) as response:
            try:
                images = await response.json()
            except ValueError as e:
                log.error("Error parsing booru JSON")
                log.error(await response.text())
                return None

        image = self.safe_shuffle(images)

        return self.dict_return(site, image)

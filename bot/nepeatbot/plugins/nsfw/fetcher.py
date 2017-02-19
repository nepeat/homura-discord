import random
import xml.etree.ElementTree as ET

from nepeatbot.plugins.nsfw.common import USER_AGENT


class ImageFetcher(object):
    def __init__(self, aiosession):
        self.aiosession = aiosession

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

        image = random.choice(images)

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

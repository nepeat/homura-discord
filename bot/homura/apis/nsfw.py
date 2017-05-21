# coding=utf-8
import logging
import random
import xml.etree.ElementTree

log = logging.getLogger(__name__)

API_ENDPOINTS = [
    # Danbooru based
    {
        "type": "danbooru",
        "endpoint": "https://e621.net/post/index.json",
        "friendly_name": "e621",
        "permalink": "https://e621.net/post/show/{}",
        "max_limit": 321
    },

    # Gelbooru based
    {
        "type": "gelbooru",
        "endpoint": "https://rule34.xxx/index.php",
        "friendly_name": "Rule 34",
        "permalink": "https://rule34.xxx/index.php?page=post&s=view&id={}",
        "max_limit": 100
    },
    {
        "type": "gelbooru",
        "endpoint": "https://gelbooru.com/index.php",
        "friendly_name": "Gelbooru",
        "permalink": "https://gelbooru.com/index.php?page=post&s=view&id={}",
        "max_limit": 100
    }
]


class FetchException(Exception):
    pass


class ImageFetcher(object):
    def __init__(self, http):
        self.http = http

    def dict_return(self, site, image):
        try:
            url = image.get("file_url")
        except AttributeError:
            return None

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
            url = image.get("file_url", "")
            if not url:
                continue

            # TIL "suffix can also be a tuple of suffixes to look for"

            if url.endswith((".webm", ".mp4", ".ogg")):
                continue

            return image

    async def gelbooru(self, site, tags, nsfw=True):
        if nsfw:
            tags = tags + " -rating:safe"

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags,
            "limit": site["max_limit"]
        }

        reply = await self.http.get(
            url=site["endpoint"],
            params=params
        )

        root = xml.etree.ElementTree.fromstring(reply)
        images = root.findall("post")

        while images:
            image = self.safe_shuffle(images)
            images.remove(image)
            metadata = self.dict_return(site, image)
            if not metadata:
                continue
            return metadata

        return None

    async def danbooru(self, site, tags, nsfw=True):
        if nsfw:
            tags = tags + " -rating:safe"

        params = {
            "tags": tags,
            "limit": site["max_limit"]
        }

        images = await self.http.get(
            url=site["endpoint"],
            params=params,
            asjson=True
        )

        if isinstance(images, dict) and not images.get("success", True):
            fail_reason = images.get("reason", "")
            if fail_reason:
                raise FetchException(fail_reason)

            raise FetchException("An unknown error occured fetching these tags.")

        while images:
            image = self.safe_shuffle(images)
            images.remove(image)
            metadata = self.dict_return(site, image)
            if not metadata:
                continue
            return metadata

        return None

    async def random(self, tags: str, nsfw: bool=True):
        image = None

        sites = API_ENDPOINTS.copy()
        while sites:
            site = random.choice(sites)
            sites.remove(site)
            if site["type"] == "gelbooru":
                image = await self.gelbooru(site, tags, nsfw)
            elif site["type"] == "danbooru":
                image = await self.danbooru(site, tags, nsfw)

            if isinstance(image, dict):
                return image

        return None

import os
import random
import urllib.parse
import warnings
from typing import Optional

from homura.lib.cached_http import CachedHTTP

GIPHY_API_ENDPOINT = "https://api.giphy.com"

class GiphyAPI(object):
    """
    This is an API that uses the Giphy API to fetch a list of gifs
    and return a single random GIF from that list.
    """
    def __init__(self, http: CachedHTTP, giphy_api_key: Optional[str]=None):
        self.http = http
        self.giphy_api_key = os.environ.get("GIPHY_API", giphy_api_key) or "dc6zaTOxFJmzC"

    async def get(self, tag: str) -> Optional[str]:
        """
        Gets a single image from Giphy given a tag.
        Returns nothing if no results were able to be found.
        """
        api_url = urllib.parse.urljoin(GIPHY_API_ENDPOINT, "/v1/gifs/search")

        images = await self.http.get(
            url=api_url,
            params={
                "api_key": self.giphy_api_key,
                "q": tag,
                "limit": 100,
                "fmt": "json"
            },
            asjson=True
        )

        if not images["data"]:
            return None

        image = random.choice(images["data"])
        image_url = image["images"]["original"]["url"]

        return {
            "permalink": image["url"],
            "image": image_url.replace("http:", "https:")
        }

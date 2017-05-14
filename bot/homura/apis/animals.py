# coding=utf-8
"""API abstraction for getting animal pictures from Imgur, The Cat API, and other sites."""

import os
import random
import urllib.parse
import xml.etree.ElementTree

IMGUR_MULTISUBS = {
    "cat": "CatsStandingUp+MEOW_IRL+StuffOnCats+cat+catReddit+catpics+cats+kitties+kitty",
    "dog": "dogpictures+dogs+lookatmydog+shiba+shibe"
}


class AnimalException(Exception):
    """This exception class is for environmental related problems relating to API keys or developer error."""
    pass


class AnimalAPI(object):
    """The abstraction class that does the fetching work."""

    def __init__(self, http):
        self.http = http

        self.imgur_api_headers = {
            "Authorization": "Client-ID " + os.environ.get("IMGUR_ID", "")
        }

        if "MASHAPE_KEY" in os.environ:
            self.imgur_api_url = "https://imgur-apiv3.p.mashape.com"
            self.imgur_api_headers.update({
                "X-Mashape-Key": os.environ["MASHAPE_KEY"]
            })
        else:
            self.imgur_api_url = "https://api.imgur.com"

    async def get(self, animal: str) -> str:
        """
            Gets a photo given an animal name.
            :param animal: Name of the animal to fetch. (Choice of cat, dog)
        """
        if "IMGUR_ID" not in os.environ:
            raise AnimalException("Imgur API key missing from environment!")

        if animal == "cat":
            use_catapi = random.choice([True, False])
            if use_catapi:
                return await self._get_catapi()

        return await self._get_imgur(animal)

    async def _get_imgur(self, animal: str):
        if animal not in IMGUR_MULTISUBS:
            raise ValueError(f"{animal} is not in IMGUR_MULTIS")

        reply = await self.http.get(
            url=urllib.parse.urljoin(self.imgur_api_url, f"3/gallery/r/{IMGUR_MULTISUBS[animal]}/time/{random.randint(1, 10)}"),
            headers=self.imgur_api_headers,
            asjson=True
        )

        if not reply["data"]:
            raise AnimalException("Zero pictures were given in the data. " + str(reply))

        image = random.choice(reply["data"])
        # Keep cycling for another link if we picked an album.
        while "/a/" in image["link"]:
            image = random.choice(reply["data"])

        return image["link"].replace("http:", "https:")

    async def _get_catapi(self):
        params = {
            "format": "xml",
            "results_per_page": "100",
            "api_key": "MTQwODc0"
        }

        reply = await self.http.get(
            url="http://thecatapi.com/api/images/get",
            params=params
        )

        root = xml.etree.ElementTree.fromstring(reply)
        images = root.findall("./data/images/image")
        image = random.choice(images).find("url").text

        return image.replace("http:", "https:")

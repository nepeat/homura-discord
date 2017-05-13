# coding=utf-8
import logging
import os
import urllib.parse

from homura.lib.structure import CommandError

log = logging.getLogger(__name__)
USER_AGENT = "github.com/nepeat/homura-discord | nepeat#6071 | This is discord bot. This is mistake."
OSU_API_BASE = "https://osu.ppy.sh/api/"


class OsuAPI(object):
    def __init__(self, aiosession):
        self.aiosession = aiosession
        self.api_key = os.environ.get("OSU_API", None)

        if not self.api_key:
            log.error("OSU_API is missing from the environment.")


    def parse_mode(self, mode):
        if mode == "osu":
            return 0
        elif mode == "taiko":
            return 1
        elif mode == "ctb":
            return 2
        elif mode == "mania":
            return 3

        raise Exception(f"Unknown mode {mode}")

    async def get_user(self, username, mode="osu"):
        if not self.api_key:
            raise CommandError("Bot is missing OSU API key.")

        params = {
            "k": self.api_key,
            "type": "string",
            "m": self.parse_mode(mode),
            "u": username
        }

        async with self.aiosession.get(
            url=urllib.parse.urljoin(OSU_API_BASE, "get_user"),
            params=params,
            headers={
                "User-Agent": USER_AGENT
            }
        ) as response:
            try:
                response = await response.json()
            except ValueError as e:
                log.error("Error parsing osu JSON")
                log.error(await response.text())
                return None

        log.error(response)

        if not response:
            return None

        return response[0]

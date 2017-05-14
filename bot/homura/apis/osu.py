# coding=utf-8
import logging
import os
import urllib.parse

from homura.lib.structure import CommandError

log = logging.getLogger(__name__)
OSU_API_BASE = "https://osu.ppy.sh/api/"


class OsuAPI(object):
    def __init__(self, http):
        self.http = http
        self.api_key = os.environ.get("OSU_API", None)

        if not self.api_key:
            log.error("OSU_API is missing from the environment.")

    @staticmethod
    def parse_mode(mode):
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

        response = await self.http.get(
            url=urllib.parse.urljoin(OSU_API_BASE, "get_user"),
            params=params,
            asjson=True
        )

        if not response:
            return None

        return response[0]

# coding=utf-8
import logging
import math

from discord import Colour, Embed
from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.plugins.osu.api import OsuAPI
from homura.util import sanitize
from homura.lib.cached_http import CachedHTTP

log = logging.getLogger(__name__)
OSU_TYPES = [
    "osu",
    "taiko",
    "ctb",
    "mania"
]

class OsuPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = OsuAPI(CachedHTTP(self.bot))

    @command(
        patterns=[
            "osu (?P<type>osu|taiko|ctb|catch the beat|mania) (?P<username>.+)",
            "osu (?P<username>.+)$",
        ],
        permission_name="osu.query",
        description="Looks up a user's stats on osu.",
        usage="osu [gamemode] <username>",
        global_command=True
    )
    async def osu(self, match):
        username = match.group("username")

        try:
            osu_type = match.group("type")
            if osu_type not in OSU_TYPES:
                osu_type = "osu"
                if match.group("type") == "catch the beat":
                    osu_type = "ctb"
        except IndexError:
            osu_type = "osu"

        info = await self.api.get_user(username, osu_type)

        if not info:
            return Message(
                f"No user named `{sanitize(username)}` was found.",
                reply=True
            )

        embed = Embed(
            title=f"osu - {username}",
            colour=Colour(0xf591bf)  # osu pink
        ).set_thumbnail(
            url="https://a.ppy.sh/" + info["user_id"]
        ).add_field(
            name="Level",
            value=int(float(info["level"] or "0")),
        ).add_field(
            name="PP",
            value=format(math.ceil(float(info["pp_raw"] or "0")), ',d'),
        ).add_field(
            name="Plays",
            value=format(int(float(info["playcount"] or "0")), ',d'),
        ).add_field(
            name=f"Rank ({info['country']})",
            value="#" + format(int(info["pp_country_rank"] or "0"), ',d')
        ).add_field(
            name="Rank (global)",
            value="#" + format(int(info["pp_rank"] or "0"), ',d')
        )

        return Message(embed=embed)

# coding=utf-8
import json
import logging
import os
from typing import Any, List, Optional, Union

import aiohttp
import discord

from homura.lib.structure import BackendError

log = logging.getLogger(__name__)


class Settings(object):
    def __init__(
        self,
        bot: Optional[discord.Client],
        identifier: str,
        prefixes: Optional[List[str]]=None
    ):
        self.bot = bot
        self.prefixes = prefixes or []
        self.identifier = identifier

    @classmethod
    async def from_guild(
        cls,
        bot: Optional[discord.Client],
        guild: Optional[discord.Guild]
    ):
        init = cls(bot, guild.id, ["server"])
        return init

    @classmethod
    async def from_channel(
        cls,
        bot: Optional[discord.Client],
        channel: Optional[Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]]
    ):
        init = cls(bot, channel.id, ["channel"])
        return init

    @property
    def redis(self):
        return self.bot.redis

    @property
    def redis_key(self) -> str:
        if self.prefixes:
            prefixes = ":".join(self.prefixes) + ":"
        else:
            prefixes = ""

        return f"botsettings:{prefixes}{identifier}"

    def __list__(self):
        return self.redis.hgetall_asdict(self.redis_key)

    async def alter(self, permission: str, remove: bool, guildwide: bool=False):
        permission = permission.strip().lower()

        if remove:
            action = self.bot.aiosession.delete
        else:
            action = self.bot.aiosession.put

        payload = {
            "server": self.guild.id,
            "channel": self.channel.id if (self.channel and not guildwide) else None,
            "perm": permission
        }

        try:
            async with action(
                url=self.backend_url + "/api/permissions/",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status in (400, 500):
                    try:
                        reply = await response.json()
                        raise BackendError(reply["message"])
                    except ValueError:
                        log.error("Failed to update permissions. {}".format(
                            await response.text()
                        ))
                        raise BackendError("Unknown error updating permissions")
        except aiohttp.ClientError:
            pass

    async def add(self, permission: str, guildwide: bool=False):
        await self.alter(permission, False, guildwide)

    async def remove(self, permission: str, guildwide: bool=False):
        await self.alter(permission, True, guildwide)

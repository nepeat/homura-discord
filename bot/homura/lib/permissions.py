# coding=utf-8
import json
import logging
import os
from typing import List, Optional

import aiohttp
import discord

from homura.lib.structure import BackendError

log = logging.getLogger(__name__)


class Permissions(object):
    def __init__(
        self,
        bot: Optional[discord.Client],
        message: Optional[discord.Message]
    ):
        self.backend_url = os.environ.get("BOT_WEB", "http://localhost:5000")
        self.bot = bot
        self.message = message
        self.guild = message.guild
        self.channel = message.channel
        self.perms = []

    @classmethod
    async def create(
        cls,
        bot: Optional[discord.Client],
        message: Optional[discord.Message]
    ):
        init = cls(bot, message)
        await init.load_perms()
        return init

    @property
    def redis(self):
        return self.bot.redis

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
        except aiohttp.errors.ClientError:
            pass

    async def add(self, permission: str, guildwide: bool=False):
        await self.alter(permission, False, guildwide)

    async def remove(self, permission: str, guildwide: bool=False):
        await self.alter(permission, True, guildwide)

    async def get_all(self):
        channel_perms = await self.get_perms()
        guild_perms = await self.get_perms(guildonly=True)

        return {
            "server": guild_perms,
            "channel": channel_perms
        }

    async def load_perms(self) -> None:
        if isinstance(self.channel, discord.abc.PrivateChannel):
            return None

        self.perms = await self.get_perms()

    async def get_perms(self, channel_id: int=None, guildonly: bool=False) -> Optional[List[str]]:
        if not channel_id:
            channel_id = self.channel.id

        params = {
            "server": self.guild.id,
            "channel": channel_id if not guildonly else None
        }
        try:
            async with self.bot.aiosession.get(
                url=self.backend_url + "/api/permissions/",
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if response.status in (400, 500):
                        log.error("Error fetching permissions.")
                        log.error(reply)

                    try:
                        return reply["permissions"]
                    except KeyError:
                        log.error("Permissions key is missing from permissions data?")
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    pass
        except aiohttp.errors.ClientError:
            pass

        return []

    def can(self, perm: str, author: Optional[discord.Member]=None, blacklist_only: bool=False) -> bool:
        if not perm:
            return True

        try:
            if author and author.guild_permissions.administrator:
                return True
        except AttributeError:
            pass

        perm = perm.strip().lower()

        if "*" in self.perms:
            return True

        # Negation checks

        negated_perm = "-" + perm

        while "." in negated_perm:
            if negated_perm in self.perms:
                return False
            negated_perm = negated_perm.rsplit(".", 1)[0]

        if negated_perm in self.perms:
            return False

        # Positive checks

        if blacklist_only:
            return True

        while "." in perm:
            if perm in self.perms:
                return True
            perm = perm.rsplit(".", 1)[0]

        if perm in self.perms:
            return True

        return False

# coding=utf-8
import json
import logging
import os

import aiohttp
import discord
from homura.lib.structure import BackendError
from typing import List, Optional

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
        self.server = message.server
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

    async def alter(self, permission, remove, serverwide=False):
        permission = permission.strip().lower()

        if remove:
            action = self.bot.aiosession.delete
        else:
            action = self.bot.aiosession.put

        payload = {
            "server": self.server.id,
            "channel": self.channel.id if (self.channel and not serverwide) else None,
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

    async def add(self, permission, serverwide=False):
        await self.alter(permission, False, serverwide)

    async def remove(self, permission, serverwide=False):
        await self.alter(permission, True, serverwide)

    async def get_all(self):
        channel_perms = await self.get_perms()
        server_perms = await self.get_perms(serveronly=True)

        return {
            "server": server_perms,
            "channel": channel_perms
        }

    async def load_perms(self) -> None:
        if self.channel.is_private:
            return None

        self.perms = await self.get_perms()

    async def get_perms(self, channel_id=None, serveronly=False) -> Optional[List[str]]:
        if not channel_id:
            channel_id = self.channel.id

        params = {
            "server": self.server.id,
            "channel": channel_id if not serveronly else None
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
            if author and author.server_permissions.administrator:
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

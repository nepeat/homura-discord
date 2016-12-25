import os
import logging

from typing import Optional

import aiohttp
import discord

log = logging.getLogger(__name__)


class Permissions(object):
    def __init__(
        self,
        bot: discord.Client,
        message: discord.Message
    ):
        self.backend_url = os.environ.get("BOT_WEB", "http://localhost:5000")

        self.bot = bot
        self.message = message
        self.server = message.server
        self.channel = message.channel

        self.perms = []
        self.bot.loop.create_task(self.load_perms())

    @property
    def redis(self):
        return self.bot.redis

    async def alter(self, permission, remove):
        permission = permission.strip().lower()

        if remove:
            action = self.bot.aiosession.delete
        else:
            action = self.bot.aiosession.put

        payload = {
            "server": self.server.id,
            "channel": self.channel.id if self.channel else None,
            "perm": permission
        }

        try:
            async with action(
                url=self.backend_url + "/api/permissions",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status in (400, 500):
                    raise Exception("Failed to update permissions. {}".format(
                        await response.text()
                    ))
        except aiohttp.errors.ClientError:
            pass

    async def add(self, permission):
        await self.alter(permission, True)

    async def remove(self, permission):
        await self.alter(permission, False)

    async def load_perms(self) -> None:
        params = {
            "server": self.server.id,
            "channel": self.channel.id
        }

        try:
            async with self.bot.aiosession.get(
                url=self.backend_url + "/perms",
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if response.status in (400, 500):
                        log.error("Error fetching permissions.")
                        log.error(reply)
                    self.perms = reply.get("permissions", [])
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
        except aiohttp.errors.ClientError:
            pass

    def can(self, perm: str) -> bool:
        perm = perm.strip().lower()

        if "*" in self.perms:
            return True

        # Permission check
        if "-" + perm in self.perms:
            return False

        while "." in perm:
            perm = perm.rsplit(".", 1)[0]
            if "-" + perm in self.perms:
                return False

        return True

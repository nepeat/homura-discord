import discord
import os

from typing import Optional

class Permissions(object):
    def __init__(
        self,
        bot: discord.Client=None,
        server: Optional[discord.Server]=None,
        member: Optional[discord.Member]=None
    ):
        self.backend_url = os.environ.get("BOT_WEB", "http://localhost:5000")

        self.bot = bot
        self.server = server
        self.member = member

        if not self.server and self.member:
            self.server = self.member.server

        self.perms = []
        self.bot.loop.create_task(self.load_perms())

    @property
    def redis(self):
        return self.bot.redis

    async def load_perms(self) -> None:
        params = {
            "server": self.server.id,
            "channel": self.channel.id
        }

        try:
            async with self.bot.aiosession.get(
                url=self.events_url + "/perms",
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("status") == "error":
                        log.error("Error pushing event to server.")
                        log.error(reply)
                    self.perms = reply.get("permissions", [])
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
        except aiohttp.errors.ClientError:
            pass

    async def can(self, perm, owner=False):
        if owner and self.member.id != "66153853824802816":
            return False

        if "*" in self.perms:
            return True

        # Implied wildcard checks
        for x in perm.split("."):
            if x in self.perms:
                return True

        # Permission check
        if perm in self.perms:
            return True

        return False

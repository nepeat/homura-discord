# coding=utf-8
import asyncio
import logging
import random
import traceback

import aiohttp
from discord import Game

from homura.plugins.common import Message, PluginBase, command

log = logging.getLogger(__name__)


class OwnerPlugin(PluginBase):
    owner_only = True
    requires_admin = True

    @command(
        "owner setgame (.+)",
        permission_name="owner.never.gonna.happen",
        description="creative description goes here."
    )
    async def set_game(self, args):
        await self.redis.hset("bot:config", "game", args[0])
        await self.bot.change_presence(
            game=Game(
                name=args[0]
            )
        )

        return Message("\N{OK HAND SIGN}")

    @command(
        "owner setname (.+)",
        permission_name="owner.never.gonna.happen",
        description="creative description goes here."
    )
    async def set_name(self, args):
        await self.bot.edit_profile(username=args[0])
        return Message("\N{OK HAND SIGN}")

    @command(
        patterns=[
            "owner setavatar (.+)",
            "owner setavatar"
        ],
        permission_name="owner.never.gonna.happen",
        description="creative description goes here."
    )
    async def set_avatar(self, message, args):
        if message.attachments:
            thing = message.attachments[0]["url"]
        else:
            if not args:
                return
            thing = args[0].strip("<>")

        try:
            with aiohttp.Timeout(10):
                async with self.bot.aiosession.get(thing) as res:
                    await self.bot.edit_profile(avatar=await res.read())
        except Exception as e:
            return Message("Unable to change avatar: {}".format(e))

        return Message("\N{OK HAND SIGN}")

    @command(
        patterns=[
            r"eval ```[\n]?[py\n](.+)```",
            r"eval (.+)"
        ],
        permission_name="owner.never.gonna.happen",
        description="According to all known laws of security, there is no way an eval should be secure."
    )
    async def eval_code(self, args, permissions, message):  # NOQA
        try:
            results = eval(args[0])
        except Exception as e:
            log.error(f"Error in eval '{args[0]}'")
            traceback.print_exc()
            return Message("```%s```" % (traceback.format_exc()))

        log.warning("Successful eval '%s'", args[0])
        log.warning(results)
        return Message("```%s```" % str(results))

    @command(
        "owner errortest",
        permission_name="owner.never.gonna.happen",
        description="Something happened."
    )
    async def errortest(self):
        return Message(1 / 0)


    @command(
        patterns=[
            "owner sleep$",
            "owner sleep (\d+)"
        ],
        permission_name="owner.never.gonna.happen",
        description="Sleeps the coroutine."
    )
    async def sleeptest(self, args):
        if args:
            sleep_time = float(args[0])
        else:
            sleep_time = random.randint(1, 5)

        await asyncio.sleep(sleep_time)
        return Message(f"Slept for {sleep_time} seconds!")

    async def on_ready(self):
        status = await self.redis.hget("bot:config", "game")

        if not status:
            return

        await self.bot.change_presence(
            game=Game(
                name=status
            )
        )

import logging
import traceback

import aiohttp
from discord import Game

from nepeatbot.plugins.common import Message, PluginBase, command

log = logging.getLogger(__name__)


class OwnerPlugin(PluginBase):
    owner_only = True
    requires_admin = True

    @command("owner setgame (.+)")
    async def set_game(self, message, args):
        await self.redis.hset("nepeatbot:config", "game", args[0])
        await self.bot.change_presence(
            game=Game(
                name=args[0]
            )
        )

        return Message("\N{OK HAND SIGN}")

    @command("owner setname (.+)")
    async def set_name(self, message, args):
        await self.bot.edit_profile(username=args[0])
        return Message("\N{OK HAND SIGN}")

    @command(patterns=[
        "owner setavatar (.+)",
        "owner setavatar"
    ])
    async def set_avatar(self, message, args):
        if message.attachments:
            thing = message.attachments[0]["url"]
        else:
            if not args:
                return
            thing = url.strip("<>")

        try:
            with aiohttp.Timeout(10):
                async with self.bot.aiosession.get(thing) as res:
                    await self.bot.edit_profile(avatar=await res.read())
        except Exception as e:
            return Message("Unable to change avatar: {}".format(e))

        return Message("\N{OK HAND SIGN}")

    @command(patterns=[
        r"eval ```[\n]?[py\n](.+)```",
        r"eval (.+)"
    ])
    async def eval_code(self, args, permissions, message):
        try:
            results = eval(args[0])
        except Exception as e:
            return Message("```%s```" % (traceback.format_exc()))

        log.warning("Successful eval '%s'", args[0])
        log.warning(results)
        return Message("```%s```" % str(results))

    async def on_ready(self):
        status = await self.redis.hget("nepeatbot:config", "game")

        if not status:
            return

        await self.bot.change_presence(
            game=Game(
                name=status
            )
        )

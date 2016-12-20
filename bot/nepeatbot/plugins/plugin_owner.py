import traceback
import logging

from discord import Game

from nepeatbot.plugins.common import PluginBase, command, Message

log = logging.getLogger(__name__)

class OwnerPlugin(PluginBase):
    is_global = True
    requires_admin = True

    @command("game (.+)", owner_only=True)
    async def set_game(self, message, args):
        await self.redis.hset("nepeatbot:config", "game", args[0])
        await self.bot.change_presence(
            game=Game(
                name=args[0]
            )
        )

        await self.bot.send_message(message.channel, "Done!")

    @command(patterns=[
        r"eval ```[\n]?[py\n](.+)```",
        r"eval (.+)"
    ], owner_only=True)
    async def eval_code(self, args, message):
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

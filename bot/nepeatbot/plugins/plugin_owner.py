from discord import Game

from nepeatbot.plugins.common import PluginBase, command

class OwnerPlugin(PluginBase):
    is_global = True
    requires_admin = True

    @command("game (.+)", owner_only=True)
    async def set_game(self, message, args):
        await self.redis.hset("nepeatbot:config", "game", args[0])
        await self.bot.change_status(
            game=Game(
                name=args[0]
            )
        )

        await self.bot.send_message(message.channel, "Done!")

    async def on_ready(self):
        status = await self.redis.hget("nepeatbot:config", "game")
        await self.bot.change_status(
            game=Game(
                name=status
            )
        )

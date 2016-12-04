import discord
from nepeatbot.plugins.common import PluginBase, command

class FunPlugin(PluginBase):
    @command("fart")
    async def fart(self, channel):
        print("FARTED")
        await self.bot.send_message(channel, "\N{DASH SYMBOL}")

    @command("egg")
    async def egg(self, message):
        em = discord.Embed(title='EGG EGG EG', description='EGGEGEGEGEGEGEG.', colour=0x416600)
        em.set_author(name='EGGEGG', icon_url="https://i.imgur.com/yuesnwm.jpg")
        em.set_footer(text="Egg.", icon_url="https://i.imgur.com/7msZamU.png")
        em.add_field(name="EGG", value="ROLLS")
        em.add_field(name="ROLL", value="EGG")
        em.set_image(url="https://i.imgur.com/YFeZaoM.jpg")
        await self.bot.send_message(message.channel, embed=em)

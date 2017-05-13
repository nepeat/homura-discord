# coding=utf-8
import datetime
import logging

import discord
from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.plugins.fun.animal_api import AnimalAPI

log = logging.getLogger(__name__)


class FunPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.animal_api = AnimalAPI(self.bot.aiosession)

    @command(
        "fart$",
        permission_name="fun.fart",
        description="Who farted?",
        global_command=True
    )
    async def fart(self, message):
        try:
            await self.bot.delete_message(message)
        except discord.Forbidden:
            pass

        return Message("\N{DASH SYMBOL}")

    @command(
        "(cat|dog)$",
        permission_name="fun.animal",
        description="Cat? Dog?",
        usage="[cat,dog]",
        global_command=True
    )
    async def animal(self, channel, args):
        start = datetime.datetime.now()
        try:
            animal_url = await self.animal_api.get(args[0])
        except Exception as e:
            await self.bot.on_error("animal")
            return Message(f"Could not fetch your {args[0]}. :(")

        embed = discord.Embed(color=discord.Colour.gold())
        embed.set_author(name=f"{args[0].capitalize()}!", url=animal_url)
        embed.set_image(url=animal_url)
        end = datetime.datetime.now()
        delta = end - start
        embed.set_footer(text="rendered in {}ms".format(int(delta.total_seconds() * 1000)))

        return Message(embed=embed)

    @command(
        "egg",
        permission_name="fun.egg",
        description="TODO: REMOVE THIS COMMAND LOL",
        global_command=True
    )
    async def egg(self, message):
        em = discord.Embed(title='EGG EGG EG', description='EGGEGEGEGEGEGEG.', colour=0x416600)
        em.set_author(name='EGGEGG', icon_url="https://i.imgur.com/yuesnwm.jpg")
        em.set_footer(text="Egg.", icon_url="https://i.imgur.com/7msZamU.png")
        em.add_field(name="EGG", value="ROLLS")
        em.add_field(name="ROLL", value="EGG")
        em.set_image(url="https://i.imgur.com/YFeZaoM.jpg")
        return Message(embed=em)

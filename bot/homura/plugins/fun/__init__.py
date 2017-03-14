# coding=utf-8
import datetime
import logging
import xml.etree.ElementTree

import discord

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class FunPlugin(PluginBase):
    @command(
        "fart",
        permission_name="fun.fart",
        description="Who farted?",
        global_command=True
    )
    async def fart(self, channel):
        return Message("\N{DASH SYMBOL}")

    @command(
        "cat",
        permission_name="fun.cat",
        description="Cat?",
        global_command=True
    )
    async def cat(self, channel):
        start = datetime.datetime.now()
        try:
            cat_url = await self.get_cat()
        except Exception as e:
            await self.bot.on_error("cat")
            return Message("Could not fetch a cat. :(")

        embed = discord.Embed(color=discord.Colour.gold())
        embed.set_author(name="Cat!", url=cat_url)
        embed.set_image(url=cat_url)
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

    async def get_cat(self):
        params = {
            "format": "xml",
            "results_per_page": "1",
            "api_key": "MTQwODc0"
        }

        async with self.bot.aiosession.get(
            url="http://thecatapi.com/api/images/get",
            params=params
        ) as response:
            reply = await response.text()

        root = xml.etree.ElementTree.fromstring(reply)
        image = root.find("./data/images/image/url").text

        return image.replace("http:", "https:")

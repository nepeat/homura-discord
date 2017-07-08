# coding=utf-8
import datetime
import logging
import os
import random
import time

import discord
from subprocess import CalledProcessError
from homura.apis.animals import AnimalAPI
from homura.apis.giphy import GiphyAPI
from homura.apis.imagemagick import MagickAbstract
from homura.lib.cached_http import CachedHTTP
from homura.lib.structure import CommandError, Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class FunPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cached_http = CachedHTTP(self.bot)
        self.animal_api = AnimalAPI(self.cached_http)
        self.giphy_api = GiphyAPI(self.cached_http)
        self.magick = MagickAbstract(self.loop)

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
    async def animal(self, args):
        start = datetime.datetime.now()
        try:
            animal_url = await self.animal_api.get(args[0])
        except:
            self.bot.on_error("animal")
            return Message(f"Could not fetch your {args[0]}. :(")

        embed = discord.Embed(color=discord.Colour.gold())
        embed.set_author(name=f"{args[0].capitalize()}!", url=animal_url)
        embed.set_image(url=animal_url)
        end = datetime.datetime.now()
        delta = end - start
        embed.set_footer(text="rendered in {}ms".format(int(delta.total_seconds() * 1000)))

        return Message(embed)

    @command(
        "(?:gif|giphy) (.+)",
        permission_name="fun.gif",
        description="Fetches a random gif with Giphy.",
        usage="gif <tag>",
        global_command=True
    )
    async def gif(self, args):
        try:
            gif = await self.giphy_api.get(args[0])
        except:
            self.bot.on_error("gif")
            return Message("Could not fetch a GIF from Giphy.")

        if not gif:
            raise CommandError(f"No results were found for '{args[0]}'.")

        embed = discord.Embed(color=discord.Colour.gold())
        embed.set_author(name=f"Giphy results for '{args[0]}'", url=gif["permalink"])
        embed.set_image(url=gif["image"])
        embed.set_footer(text="Results powered by Giphy.")

        return Message(embed)

    @command(
        "egg",
        permission_name="fun.egg",
        description="TODO: REMOVE THIS COMMAND LOL",
        global_command=True
    )
    async def egg(self):
        em = discord.Embed(title='EGG EGG EG', description='EGGEGEGEGEGEGEG.', colour=0x416600)
        em.set_author(name='EGGEGG', icon_url="https://i.imgur.com/yuesnwm.jpg")
        em.set_footer(text="Egg.", icon_url="https://i.imgur.com/7msZamU.png")
        em.add_field(name="EGG", value="ROLLS")
        em.add_field(name="ROLL", value="EGG")
        em.set_image(url="https://i.imgur.com/YFeZaoM.jpg")
        return Message(em)

    @command(
        "coin",
        permission_name="fun.coin",
        description="Flips a coin!",
        global_command=True
    )
    async def coin(self):
        landing = "The coin lands on {land}".format(
            land=random.choices(["heads", "tails", "its side"], [49, 49, 2])[0]
        )

        embed = discord.Embed(
            title="Coin flip!",
            colour=discord.Colour.gold(),
            description=landing
        )

        return Message(embed)

    @command(
        patterns=[
            r"dice (?P<dice>\d+)[d,](?P<sides>\d+)",
            r"dice (?P<dice>\d+) dice (?P<sides>\d+) sides",
            r"dice (?P<sides>\d+) sides (?P<dice>\d+) dice",
            "dice$",
        ],
        permission_name="fun.dice",
        description="Rolls dice!",
        global_command=True
    )
    async def dice(self, match):
        try:
            sides = int(match.group("sides"))
            die = int(match.group("dice"))
        except IndexError:
            sides = 6
            die = 2

        if sides > 10000:
            raise CommandError(f"Seriously? {sides} sides?")

        if die > 1000:
            raise CommandError(f"Seriously? {die} dice?")

        landing = "The coin lands on {land}".format(
            land=random.choices(["heads", "tails", "on its side"], [49.5, 49.5, 1])
        )

        embed = discord.Embed(
            title=f"Rolling {die} dice with {sides} sides",
            colour=discord.Colour.dark_blue(),
        )

        die_values = [random.randint(1, sides) for x in range(0, die)]
        die_counts = ""

        for index, value in enumerate(die_values):
            if index == len(die_values) - 1:
                die_append = f"{value}"
            else:
                die_append = f"{value} + "

            max_len = len(die_append) + len(die_counts) + len("... + " + str(die_values[-1]))
            if max_len > 1000:
                die_counts += f"... + {die_values[-1]}"
                break

            die_counts += die_append

        embed.add_field(
            name="Rolls",
            value=die_counts
        )

        total = 0
        for x in die_values:
            total += x
        embed.add_field(
            name="Total",
            value=str(total)
        )

        return Message(embed)

    @command(
        patterns=[
            "morejpg (\d+)",
            "morejpg$",
        ],
        permission_name="fun.morejpg",
        description="Corrupts a JPG.",
        global_command=True
    )
    async def morejpg(self, message, args):
        try:
            quality = int(args[0])
            if quality < 1 or quality > 100:
                raise ValueError()
        except (IndexError, ValueError):
            quality = 10

        if not message.attachments:
            raise CommandError("Please attach an image to corrupt.")

        image_url = message.attachments[0].url
        async with self.bot.aiosession.get(
            url=image_url,
        ) as response:
            image_data = await response.read()

        try:
            await self.magick.validate(image_data)
        except CalledProcessError:
            raise CommandError("Image uploaded is not a valid image.")

        filename = "morejpg-" + str(int(time.time())) + "-" + image_url.split("/")[-1]

        return Message.from_file(
            data=await self.magick.jpg_compress(image_data, quality),
            filename=filename
        )

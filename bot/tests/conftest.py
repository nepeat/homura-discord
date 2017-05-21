import logging
import os
import random
import traceback

import aiohttp
import asyncio
import asyncio_redis
import discord
import pytest
from homura.lib.redis_mods import BotEncoder, UncheckedRedisProtocol
from homura.lib.structure import Message
from homura.lib.util import Dummy
from homura.plugins.manager import PluginManager

from . import create_unique_id

log = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true",
        help="run slow tests")


class MockUser():
    def __init__(self):
        self._id = create_unique_id()

    @property
    def id(self):
        return self._id


class MinimalBot(object):
    def __init__(self, redis, aiosession):
        self.redis = redis
        self.aiosession = aiosession

        # Test suite logging
        self._log = []

        # Plugin manager holdings
        self.plugins = PluginManager(self)
        self.all_permissions = set()

        # Other mocks
        self.user = MockUser()
        self.stats = Dummy()

    @property
    def loop(self):
        return asyncio.get_event_loop()

    @staticmethod
    async def create_redis():
        return await asyncio_redis.Pool.create(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 0)),
            poolsize=2,
            encoder=BotEncoder(),
            protocol_class=UncheckedRedisProtocol
        )

    @staticmethod
    async def send(self, content: str=None, embed: discord.Embed=None):
        if content:
            log.info(content)

        if embed:
            if embed.title:
                log.info(embed.title)
            if embed.description:
                log.info(embed.description)
            for field in embed.fields:
                log.info(f"\t{field.name}")
                log.info(f"\t{field.value}")
            if embed.footer:
                log.info(embed.footer)

    @classmethod
    async def init(cls):
        redis = await cls.create_redis()
        aiosession = aiohttp.ClientSession()

        return cls(redis, aiosession)

    async def send_message_object(self, message: Message, *args, **kwargs):
        log.info(message.content)
        if message.reply:
            log.info("Message is a reply.")
        if message.delete_after:
            log.info(f"Message will be deleted after {message.delete_after}.")
        if message.delete_invoking:
            log.info(f"Invoking will be deleted after {message.delete_invoking}.")

    def on_error(self, namespace=""):
        log.error(f"Namespace error caught. ({namespace})")
        traceback.print_exc()

@pytest.fixture
async def bot():
    return await MinimalBot.init()


@pytest.fixture
def author():
    author = discord.Object(
        id=create_unique_id()
    )
    author.discriminator=random.randint(1, 9999)
    author.name="Fake Author"
    author.guild_permissions = discord.Object(
        id=create_unique_id()
    )
    author.guild_permissions.administrator = False
    author.guild_permissions.manage_guild = False

    return author


@pytest.fixture
def channel():
    channel = discord.Object(
        id=create_unique_id()
    )
    channel.name = "fake-channel"
    channel.send = MinimalBot.send

    return channel


@pytest.fixture
def guild():
    guild = discord.Object(
        id=create_unique_id()
    )
    guild.name = "The Fake Server"

    return guild


@pytest.fixture
def message(author, channel, guild):
    message = discord.Object(
        id=create_unique_id()
    )

    message.author = author
    message.channel = channel
    message.guild = guild
    message.content = "Message content."
    message.clean_content = "Message content."

    return message

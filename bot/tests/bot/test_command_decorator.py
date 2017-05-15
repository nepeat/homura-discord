'''
    I regret making this decorator complicated.
    (but hey we have "tests" for this decorator)

    05/15/17, 1:11 AM - The conftest.py is becoming godawful but it works and sorta mocks out what I need?
'''

import pytest
from typing import List, Tuple
import discord

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.plugins.manager import PluginManager
from .. import create_unique_id

class DummyPlugin(PluginBase):
    @command(
        "owneronly",
        owner_only=True
    )
    async def owner_command(self, message):
        return Message("owner=true")

    @command(
        "kek",
        permission_name="test.test",
        description="Test command.",
        global_command=True
    )
    async def single_pattern(self):
        return Message("SINGLEPATTERN")

    @command(
        patterns=[
            "test$",
            "catch (.+)"
        ],
        permission_name="test.test",
        description="Test command.",
        global_command=True
    )
    async def test_command(self, args):
        if args and args[0]:
            return Message(args[0])

        return Message("TESTCOMMAND")

    @command(
        "nonglobal$",
        permission_name="test.restricted",
        description="Test command, non global."
    )
    async def nonglobal(self, author):
        return Message(f"AUTHORIZED:{author.id}")

@pytest.fixture
async def dummy_plugin(bot):
    bot = await bot
    manager = PluginManager(bot)
    manager.load(DummyPlugin)

    return manager.get("dummy")


"""
Permission based tests.
* Owner only command run by non owner and owner.
* User and server admin running command not granted by permissions.
* User running command granted by permissions.
* User running command blacklisted by permissions.
"""

async def run_normal_admin_owner(
    command,
    plugin: PluginBase,
    message: discord.Message,
    numusers: int=1
) -> Tuple[List[int], int]:
    """
    Runs a command under the normal, admin, owner user tiers.

    :param command: The command to run.
    :param plugin: A plugin object that has an _on_message handler.
    :param message: A mock Message.
    :param numusers: Number of users to test.
    :return: (user_id, admin_id)
    """
    if numusers < 0:
        raise Exception("Number of users must be greater than or equal to zero.")

    message.content = command

    # Test for users running the command.
    user_ids = [
        create_unique_id() for x in range(0, numusers)
    ]

    for user_id in user_ids:
        message.author.id = user_id
        await plugin._on_message(message)

    # Test for admin running the command
    message.author.id = admin_id = create_unique_id()
    message.author.guild_permissions.administrator = True
    await plugin._on_message(message)
    message.author.guild_permissions.administrator = False

    # Test for owner running the command.
    message.author.id = 66153853824802816
    await plugin._on_message(message)

    return user_ids, admin_id


@pytest.mark.asyncio
async def test_owner_only(dummy_plugin, message, caplog):
    dummy_plugin = await dummy_plugin

    await run_normal_admin_owner("!owneronly", dummy_plugin, message)

    # Assert all possibilities happened.
    assert sum(1 for x in caplog.records if "ಠ_ಠ" in x.msg) == 2
    assert any("owner=true" in x.msg for x in caplog.records)


@pytest.mark.asyncio
async def test_nonglobal_command(dummy_plugin, message, caplog):
    dummy_plugin = await dummy_plugin
    message.content = "!nonglobal"

    await run_normal_admin_owner("!nonglobal", dummy_plugin, message, numusers=4)

    # Assert that tests has been successful.
    assert sum(1 for x in caplog.records if "You are not allowed" in x.msg) == 4
    assert sum(1 for x in caplog.records if "AUTHORIZED" in x.msg) == 2


@pytest.mark.asyncio
async def test_granted_permissions(monkeypatch, dummy_plugin, message, caplog):
    async def patched_perms(*args, **kwargs):
        return ["test.restricted"]

    monkeypatch.setattr("homura.lib.permissions.Permissions.get_perms", patched_perms)
    dummy_plugin = await dummy_plugin

    await run_normal_admin_owner("!nonglobal", dummy_plugin, message, numusers=4)

    # Assert that tests has been successful.
    assert sum(1 for x in caplog.records if "You are not allowed" in x.msg) == 0
    assert sum(1 for x in caplog.records if "AUTHORIZED" in x.msg) == 6


@pytest.mark.asyncio
async def test_denied_permissions(monkeypatch, dummy_plugin, message, caplog):
    async def patched_perms(*args, **kwargs):
        return ["-test"]

    monkeypatch.setattr("homura.lib.permissions.Permissions.get_perms", patched_perms)
    dummy_plugin = await dummy_plugin

    await run_normal_admin_owner("!kek", dummy_plugin, message, numusers=4)

    # Assert that tests has been successful.
    assert sum(1 for x in caplog.records if "You are not allowed" in x.msg) == 4
    assert sum(1 for x in caplog.records if "SINGLEPATTERN" in x.msg) == 2


"""
Command trigger tests.
* Tagging the bot with the normal prefix
* Tagging the bot with its mention.
* Multiple pattern commands with a match
* Single pattern commands
"""


@pytest.mark.asyncio
async def test_multi_triggers_normal_and_mention(bot, dummy_plugin, message, caplog):
    dummy_plugin = await dummy_plugin

    # Test for the normal ! prefix.
    message.content = "!test"
    await dummy_plugin._on_message(message)

    # Test for the bot's mention as a prefix.
    message.content = f"<@{dummy_plugin.bot.user.id}> catch ARGUMENT_REAL"
    await dummy_plugin._on_message(message)

    # Test for the bot's nickname mention as a prefix.
    message.content = f"<@!{dummy_plugin.bot.user.id}> catch ARGUMENT_NICK"
    await dummy_plugin._on_message(message)

    # Assert that tests has been successful.
    assert_has = ["TESTCOMMAND", "ARGUMENT_REAL", "ARGUMENT_NICK"]
    for has in assert_has:
        assert any(has in x.msg for x in caplog.records)


@pytest.mark.asyncio
async def test_single_triggers_normal_and_mention(bot, dummy_plugin, message, caplog):
    dummy_plugin = await dummy_plugin

    # Test for the normal ! prefix.
    message.content = "!kek"
    await dummy_plugin._on_message(message)

    # Test for the bot's mention as a prefix.
    message.content = f"<@{dummy_plugin.bot.user.id}> kek"
    await dummy_plugin._on_message(message)

    # Test for the bot's nickname mention as a prefix.
    message.content = f"<@!{dummy_plugin.bot.user.id}> kek"
    await dummy_plugin._on_message(message)

    # Assert that test_command has been executed three times.
    assert sum(1 for x in caplog.records if "SINGLEPATTERN" in x.msg) == 3

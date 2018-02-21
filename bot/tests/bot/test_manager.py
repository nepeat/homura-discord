import pytest

from homura.plugins.base import PluginBase
from homura.plugins.command import command
from homura.plugins.manager import PluginManager


class DummyPlugin(PluginBase):
    @command(
        "test"
    )
    def bad_command(self):
        return "Where is my metadata?"

@pytest.mark.asyncio
async def test_manager_load_all(bot):
    assert len(bot.plugins) == 0
    assert len(bot.all_permissions) == 0
    bot.plugins.load_all()
    assert len(bot.all_permissions) > 0
    assert len(bot.plugins) > 0


@pytest.mark.asyncio
async def test_manager_get_plugins(bot, caplog):
    bot.plugins.load_all()

    # Getting plugins with get() method.
    assert bot.plugins.get("Settings")
    assert bot.plugins.get("   SeTtIngS   ")
    assert not bot.plugins.get("lol fake plugin")

    # Getting plugins with attributes.
    assert bot.plugins.settings
    assert bot.plugins.Settings
    assert not bot.plugins.lol_fake_plugin

    # Getting plugins with indexes.
    assert bot.plugins["SEttings "]
    assert not bot.plugins["FAKEEE"]

    for log in caplog.records:
        assert "missing a description" not in log.msg
        assert "does not have a permission" not in log.msg


@pytest.mark.asyncio
async def test_manager_load_dummy(bot, caplog):
    bot.plugins.load(DummyPlugin)

    dummy_init = bot.plugins.get("dummy")

    assert dummy_init

    logstrings = [
        "DummyPlugin is missing a description",
        "DummyPlugin does not have a permission",
    ]

    for log_expect in logstrings:
        found = False

        for log in caplog.records:
            if log_expect in log.msg:
                found = True

        assert found

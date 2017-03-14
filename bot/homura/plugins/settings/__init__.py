# coding=utf-8
import logging
from itertools import zip_longest

from homura.plugins.common import Message, PluginBase, command

log = logging.getLogger(__name__)


class SettingsPlugin(PluginBase):
    @command(
        "settings get logchannel$",
        permission_name="settings.get.logchannel",
        description="Gets the moderation logging channel."
    )
    async def get_log_channel(self, message):
        log_channel = await self.redis.hget(f"{message.server.id}:settings", "log_channel")
        if log_channel:
            return Message(f"The log channel is <#{log_channel}>")

        return Message(f"You do not have a logging channel set! Set one with {self.cmd_prefix}settings set logchannel")

    @command(
        "settings set logchannel$",
        permission_name="settings.set.logchannel",
        description="Sets the moderation logging channel."
    )
    async def set_log_channel(self, message):
        await self.redis.hset(f"{message.server.id}:settings", "log_channel", message.channel.id)
        return Message("Updated!")

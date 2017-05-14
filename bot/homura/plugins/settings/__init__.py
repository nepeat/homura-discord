# coding=utf-8
import logging
from itertools import zip_longest

from homura.lib.structure import Message
from homura.plugins.base import PluginBase
from homura.plugins.command import command

log = logging.getLogger(__name__)


class SettingsPlugin(PluginBase):
    @command(
        "settings get logchannel$",
        permission_name="settings.get.logchannel",
        description="Gets the moderation logging channel.",
        usage="settings get logchannel"
    )
    async def get_log_channel(self, message):
        log_channel = await self.redis.hget(f"{message.server.id}:settings", "log_channel")
        if log_channel:
            return Message(f"The log channel is <#{log_channel}>")

        return Message(f"You do not have a logging channel set! Set one with {self.cmd_prefix}settings set logchannel")

    @command(
        "settings set logchannel$",
        permission_name="settings.set.logchannel",
        description="Sets the moderation logging channel.",
        usage="settings set logchannel"
    )
    async def set_log_channel(self, message):
        await self.redis.hset(f"{message.server.id}:settings", "log_channel", message.channel.id)
        return Message("Updated!")

    @command(
        "settings imagechannel (enable|on|disable|off)$",
        permission_name="settings.set.imagechannel",
        description="Toggles the image only mode.",
        usage="settings imagechannel [enable|disable]"
    )
    async def toggle_imagechannel(self, message, args):
        action = self.redis.sadd if args[0] in ("enable", "on") else self.redis.srem
        await action("antispam:imagechannels", [message.channel.id])

        return Message("Updated!")

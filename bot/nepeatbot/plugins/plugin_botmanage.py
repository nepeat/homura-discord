from nepeatbot.plugins.common import PluginBase, command

class BotManagerPlugin(PluginBase):
    is_global = True
    requires_admin = True

    @command("plugin(?:\s(?:help|list)|$)")
    async def list_plugins(self, message):
        result = "**__Plugins__**\n"
        result = result + "\n".join([plugin.__class__.__name__.replace("Plugin", "") for plugin in self.bot.plugins if not plugin.is_global])

        await self.bot.send_message(message.channel, result)

    @command("plugin (?:on|enable) (.+)")
    async def enable_plugin(self, message, args):
        await self.update_plugin(message, args[0], True)

    @command("plugin (?:off|disable) (.+)")
    async def disable_plugin(self, message, args):
        await self.update_plugin(message, args[0], False)

    async def update_plugin(self, message, plugin_name: str, enabled: bool):
        plugin = self.bot.plugin_manager.get(plugin_name)

        if not plugin:
            await self.bot.send_message(message.channel, "Plugin `{plugin}` is not valid!".format(
                plugin=plugin_name
            ))
            return

        if plugin.is_global:
            await self.bot.send_message(message.channel, "Plugin `{plugin}` is a global plugin!".format(
                plugin=plugin_name
            ))
            return

        action = self.bot.redis.sadd if enabled else self.bot.redis.srem
        await action("plugins:{}".format(message.server.id), [plugin.__class__.__name__])

        await self.bot.send_message(message.channel, "Plugin {status}!".format(
            status="enabled \N{CHECK MARK}" if enabled else "disabled \N{CROSS MARK}"
        ))

import aiohttp
import re

from nepeatbot.plugins.common import PluginBase, command

class QuotesPlugin(PluginBase):
    is_global = True
    url_regex = re.compile(r"(https?:\/\/\S+)")

    @command("quote status")
    async def plugin_status(self, channel):
        status = await self.bot.redis.sismember("quotes:channels", channel.id)
        await self.bot.send_message(channel, "Quotes is {status}".format(
            status="enabled \N{WHITE HEAVY CHECK MARK}" if status else "disabled \N{CROSS MARK}"
        ))

    @command("quote (enable|on|disable|off)")
    async def plugin_state(self, channel, args):
        if args[0].lower() in ["enable", "on"]:
            action = self.bot.redis.sadd
        else:
            action = self.bot.redis.srem

        await action("quotes:channels", [channel.id])
        await self.bot.send_message(channel, "\N{WHITE HEAVY CHECK MARK}")

    async def on_message(self, message):
        if await self.bot.redis.sismember("quotes:channels", message.channel.id):
            await self.handle_quote(message)

    async def validate_url(self, url):
        with aiohttp.Timeout(10):
            try:
                async with self.bot.aiosession.get(url) as response:
                    if response.headers:
                        return True

                    return False
            except aiohttp.errors.ClientError:
                return False

    async def handle_quote(self, message):
        content = message.content.lower()
        urls = QuotesPlugin.url_regex.search(content)

        if message.attachments:
            return
        elif urls:
            for url in urls.groups():
                if not await self.validate_url(url):
                    return await self.bot.delete_message(message)
        else:
            await self.bot.delete_message(message)

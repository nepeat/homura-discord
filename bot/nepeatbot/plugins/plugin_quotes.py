import aiohttp
import re

from nepeatbot.plugins.common import PluginBase, command

class QuotesPlugin(PluginBase):
    url_regex = re.compile(r"(https?:\/\/\S+)")

    async def validate_url(self, url):
        with aiohttp.Timeout(10):
            try:
                async with self.bot.aiosession.get(url) as response:
                    if response.headers:
                        return True

                    return False
            except aiohttp.errors.ClientError:
                return False

    async def handle_quote(self, message, bot):
        content = message.content.lower()
        urls = QuotesPlugin.url_regex.search(content)

        if message.attachments:
            return
        elif urls:
            for url in urls.groups():
                if not await self.validate_url(bot.aiosession, url):
                    return await self.delete_message(message)
        else:
            await self.delete_message(message)

    async def on_message(self, message):
        if message.channel.id == "195245746612731904":  # XXX quote-only legacy
            await self.handle_quote(message)

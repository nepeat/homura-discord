import logging
import os
import re

import aiohttp

from nepeatbot.plugins.common import Message, PluginBase, command

log = logging.getLogger(__name__)

class AntiNSFWPlugin(PluginBase):
    requires_admin = True
    url_regex = re.compile(r"(https?://\S+)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nsfw_url = os.environ.get("NSFWAPI_URL", "http://localhost:5001")

    @command("antinsfw")
    async def antinsfw_status(self):
        return Message("implement me lol")

    @command("antinsfw (enable|disable)")
    async def toggle_event(self, message, args):
        action = self.bot.redis.sadd if args[0] == "enable" else self.bot.redis.srem

        await action("antinsfw:enabled", message.server.id)

        return Message("Updated!")

    @command("antinsfw status")
    async def antinsfw_status(self):
        return Message("implement me lol")

    async def on_message(self, message):
        enabled = await self.redis.sismember("antinsfw:enabled", message.server.id)
        if not enabled:
            return

        for embed in message.embeds:
            if "thumbnail" not in embed:
                continue

            if "proxy_url" not in embed["thumbnail"]:
                continue

            response = await self.check_image(embed["thumbnail"]["proxy_url"])
            if response.get("nsfw", False):
                return await self.bot.send_message(message.channel, "OH JESUS IT'S FUCKED UP SHIT")

        urls = AntiNSFWPlugin.url_regex.search(message.content)
        if urls:
            for url in urls.groups():
                response = await self.check_image(url)
                if response.get("nsfw", False):
                    return await self.bot.send_message(message.channel, "OH JESUS IT'S FUCKED UP SHIT")

    async def check_image(self, image_url, **kwargs):
        params = {
            "url": image_url,
        }

        if kwargs:
            params.update(kwargs)

        log.debug(params)

        try:
            async with self.bot.aiosession.get(
                url=self.nsfw_url + "/check",
                params=params
            ) as response:
                try:
                    reply = await response.json()
                    if reply.get("error"):
                        log.error("Error pushing event to server.")
                        log.error(reply)
                        return {}
                    return reply
                except ValueError:
                    log.error("Error parsing JSON.")
                    log.error(await response.text())
                    pass
        except aiohttp.errors.ClientError:
            pass

        return {}

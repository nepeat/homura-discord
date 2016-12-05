import asyncio
import re
import inspect
import logging

from functools import wraps

log = logging.getLogger(__name__)


class Message(object):
    def __init__(self, content, reply=False, delete_after=0, delete_invoking=False):
        self.content = content
        self.reply = reply
        self.delete_after = delete_after
        self.delete_invoking = delete_invoking


def command(pattern=None, description="", usage=None, requires_admin=False, owner_only=False):
    if not pattern.startswith("^!"):
        pattern = "^!" + pattern

    def actual_decorator(func):
        prog = re.compile(pattern)

        @wraps(func)
        async def wrapper(self, message):

            # Is it matching?
            match = prog.match(message.content)
            if not match:
                return

            self.bot.stats.incr("nepeatbot.command,function=" + func.__name__)

            args = match.groups()
            author = message.author

            is_admin = (
                author.server_permissions.manage_server or
                author.server_permissions.administrator or
                author.id == "66153853824802816"
            )

            # Checking roles
            if requires_admin and not is_admin:
                return

            if owner_only and author.id != "66153853824802816":
                return

            log.info("{}#{}@{} >> {}".format(message.author.name,
                                             message.author.discriminator,
                                             message.server.name,
                                             message.clean_content))

            handler_kwargs = {}

            argspec = inspect.signature(func)
            params = argspec.parameters.copy()

            if params.pop("self", None):
                handler_kwargs['self'] = self

            if params.pop("bot", None):
                handler_kwargs['bot'] = self.bot

            if params.pop('message', None):
                handler_kwargs['message'] = message

            if params.pop('channel', None):
                handler_kwargs['channel'] = message.channel

            if params.pop('author', None):
                handler_kwargs['author'] = message.author

            if params.pop('server', None):
                handler_kwargs['server'] = message.server

            if params.pop('user_mentions', None):
                handler_kwargs['user_mentions'] = list(map(message.server.get_member, message.raw_mentions))

            if params.pop('channel_mentions', None):
                handler_kwargs['channel_mentions'] = list(map(message.server.get_channel, message.raw_channel_mentions))

            if params.pop('args', None):
                handler_kwargs['args'] = args

            response = await func(**handler_kwargs)
            if response and isinstance(response, Message):
                content = response.content
                if response.reply:
                    content = '{}, {}'.format(message.author.mention, content)

                sentmsg = await self.bot.send_message(
                    message.channel, content
                )

                if response.delete_after:
                    await asyncio.sleep(response.delete_after)
                    await self.bot.delete_message(sentmsg)

                if response.delete_invoking:
                    await asyncio.sleep(5)
                    self.bot.delete_message(message)

        wrapper._is_command = True
        if usage:
            command_name = usage
        else:
            command_name = "!" + func.__name__
        wrapper.info = {"name": command_name,
                        "description": description}
        return wrapper
    return actual_decorator

class PluginBase(object):
    is_global = False

    def __init__(self, bot):
        self.bot = bot
        self.commands = {}

        for name, member in inspect.getmembers(self):
            # registering commands
            if hasattr(member, '_is_command'):
                self.commands[member.__name__] = member
        log.info("Registered {commands} commands".format(
            commands=len(self.commands)
        ))

    @property
    def redis(self):
        return self.bot.redis

    async def on_ready(self):
        pass

    async def _on_message(self, message):
        if message.author.id != self.bot.user.id:
            for command_name, func in self.commands.items():
                await func(message)
        await self.on_message(message)

    async def on_message(self, message):
        pass

    async def on_message_edit(self, before, after):
        pass

    async def on_message_delete(self, message):
        pass

    async def on_channel_create(self, channel):
        pass

    async def on_channel_update(self, before, after):
        pass

    async def on_channel_delete(self, channel):
        pass

    async def on_member_join(self, member):
        pass

    async def on_member_remove(self, member):
        pass

    async def on_member_update(self, before, after):
        pass

    async def on_server_join(self, server):
        pass

    async def on_server_update(self, before, after):
        pass

    async def on_server_role_create(self, role):
        pass

    async def on_server_role_delete(self, role):
        pass

    async def on_server_role_update(self, server, role):
        pass

    async def on_voice_state_update(self, before, after):
        pass

    async def on_member_ban(self, member):
        pass

    async def on_member_unban(self, member):
        pass

    async def on_typing(self, channel, user, when):
        pass

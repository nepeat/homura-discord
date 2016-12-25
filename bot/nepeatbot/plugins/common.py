import asyncio
import re
import inspect
import logging

from functools import wraps

from nepeatbot.lib.permissions import Permissions

log = logging.getLogger(__name__)


class Message(object):
    def __init__(self, content=None, embed=None, reply=False, delete_after=0, delete_invoking=False):
        self.content = content
        self.embed = embed
        self.reply = reply
        self.delete_after = delete_after
        self.delete_invoking = delete_invoking


def command(
    pattern=None,
    description="",
    usage=None,
    requires_admin=False,
    owner_only=False,
    patterns=[],
    permission_name=None
):
    if pattern and not pattern.startswith("^!"):
        _patterns = ["^!" + pattern]
    elif patterns:
        _patterns = [("^!" + x) if x else x for x in patterns]

    def actual_decorator(func):
        progs = [re.compile(p) for p in _patterns]

        @wraps(func)
        async def wrapper(self, message):

            # Is it matching?
            match = None
            for prog in progs:
                log.debug("prog %s" % (prog))
                match = prog.match(message.content)
                log.debug("matching %s" % (match))
                if match:
                    break

            if not match:
                return

            self.bot.stats.incr("nepeatbot.command,function=" + func.__name__)

            permissions = Permissions(
                self.bot,
                message
            )

            args = match.groups()
            author = message.author

            # Bot owner check
            if owner_only and author.id != "66153853824802816":
                log.warning("%s#%s [%s] has attempted to run owner command `%s`.",
                    author.name,
                    author.discriminator,
                    author.id,
                    func.__name__
                )
                self.bot.send_message_object(Message(
                    content="ಠ_ಠ",
                    reply=True,
                    delete_after=True,
                    delete_invoking=True
                ))
                return

            # Admin check
            is_admin = (
                author.server_permissions.manage_server or
                author.server_permissions.administrator or
                author.id == "66153853824802816"
            )

            if (requires_admin or self.requires_admin) and not is_admin:
                self.bot.send_message_object(Message(
                    content="You need administrator role permissions to use this command.",
                    reply=True,
                    delete_after=True,
                    delete_invoking=True
                ))
                return

            # Permissions check
            if not permissions.can(permission_name):
                self.bot.send_message_object(Message(
                    content="You are not allowed to use this command in this server or channel.",
                    reply=True,
                    delete_after=True,
                    delete_invoking=True
                ))
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

            if params.pop('match', None):
                handler_kwargs['match'] = match

            if params.pop('args', None):
                handler_kwargs['args'] = args

            if params.pop('permissions', None):
                handler_kwargs['permissions'] = permissions

            response = await func(**handler_kwargs)
            if response and isinstance(response, Message):
                self.bot.send_message_object(response, message.author)

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
    requires_admin = False

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

    async def on_member_unban(self, server, member):
        pass

    async def on_typing(self, channel, user, when):
        pass

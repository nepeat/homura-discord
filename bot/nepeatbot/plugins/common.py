import inspect
import logging
import re
from functools import wraps

import discord

import asyncio
from nepeatbot.lib.permissions import Permissions
from nepeatbot.lib.signals import BackendError

log = logging.getLogger(__name__)

OWNER_IDS = [
    "66153853824802816"
]


class Message(object):
    def __init__(self, content=None, embed=None, reply=False, delete_after=0, delete_invoking=0):
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
    permission_name="",
    global_command=False,
):

    if pattern and not pattern.startswith("^!"):
        _patterns = ["^!" + pattern]
    elif patterns:
        _patterns = [("^!" + x) if x else x for x in patterns]

    def actual_decorator(func):
        progs = [re.compile(p) for p in _patterns]

        @wraps(func)
        async def wrapper(self, message):

            # Command match

            match = None
            for prog in progs:
                log.debug("prog %s" % (prog))
                match = prog.match(message.content)
                log.debug("matching %s" % (match))
                if match:
                    break

            if not match:
                # Fallback with the bot's mention tag
                match = re.match("<[!@]{{1,2}}{userid}> {pattern}".format(
                    userid=self.bot.user.id,
                    pattern=pattern
                ), message.content)
                if not match:
                    return

            # Analytics and setup

            self.bot.stats.incr("nepeatbot.command,function=" + func.__name__)

            permissions = await Permissions.create(
                self.bot,
                message
            )
            args = match.groups()
            author = message.author

            # Bot owner check

            if (owner_only or self.owner_only) and author.id not in OWNER_IDS:
                log.warning(
                    "%s#%s [%s] has attempted to run owner command `%s`.",
                    author.name,
                    author.discriminator,
                    author.id,
                    func.__name__
                )
                await self.bot.send_message_object(
                    Message(
                        content="ಠ_ಠ",
                        reply=True,
                        delete_after=10,
                        delete_invoking=10
                    ),
                    message.channel,
                    message.author,
                    message
                )
                return

            # Admin check

            try:
                is_admin = (
                    author.server_permissions.manage_server or
                    author.server_permissions.administrator or
                    author.id in OWNER_IDS
                )
            except AttributeError:
                is_admin = author.id in OWNER_IDS

            if (requires_admin or self.requires_admin) and not is_admin:
                await self.bot.send_message_object(
                    Message(
                        content="You need administrator role permissions to use this command.",
                        reply=True,
                        delete_after=10,
                        delete_invoking=10
                    ),
                    message.channel,
                    message.author,
                    message
                )
                return

            # Permissions check

            if not permissions.can(permission_name, author, global_command) and author.id not in OWNER_IDS:
                await self.bot.send_message_object(
                    Message(
                        content="You are not allowed to use this command in this server or channel.",
                        reply=True,
                        delete_after=10,
                        delete_invoking=10
                    ),
                    message.channel,
                    message.author,
                    message
                )
                return

            log.info("{}#{}@{} >> {}".format(message.author.name,
                                             message.author.discriminator,
                                             message.server.name if message.server else "PM",
                                             message.clean_content))

            # Parameters for the command function.

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

            # Command caller

            try:
                response = await func(**handler_kwargs)
            except BackendError as e:
                return await self.bot.send_message(message.channel, str(e))
            except Exception as e:
                embed = discord.Embed(
                    title="Something happened",
                    description="An error happened running this command",
                    color=discord.Colour.red()
                )
                sentry_code = await self.bot.on_error("command:" + func.__name__)
                if sentry_code:
                    embed.set_footer(text=sentry_code)

                return await self.bot.send_message(message.channel, embed=embed)

            if response and isinstance(response, Message):
                await self.bot.send_message_object(response, message.channel, message.author, message)

        wrapper._is_command = True
        if usage:
            command_name = usage
        else:
            command_name = "!" + func.__name__
        wrapper.info = {
            "name": command_name,
            "description": description,
            "permission": permission_name,
            "global": global_command
        }
        return wrapper
    return actual_decorator


class PluginBase(object):
    """
        .. function:: on_ready()
        .. function:: on_resumed()
        .. function:: on_error(event, \*args, \*\*kwargs)
        .. function:: on_message(message)
        .. function:: on_socket_raw_receive(msg)
        .. function:: on_socket_raw_send(payload)
        .. function:: on_message_delete(message)
        .. function:: on_message_edit(before, after)
        .. function:: on_reaction_add(reaction, user)
        .. function:: on_reaction_remove(reaction, user)
        .. function:: on_reaction_clear(message, reactions)
        .. function:: on_channel_delete(channel)
        .. function:: on_channel_update(before, after)
        .. function:: on_member_join(member)
        .. function:: on_member_update(before, after)
        .. function:: on_server_join(server)
        .. function:: on_server_remove(server)
        .. function:: on_server_update(before, after)
        .. function:: on_server_role_create(role)
        .. function:: on_server_role_update(before, after)
        .. function:: on_server_emojis_update(before, after)
        .. function:: on_server_available(server)
        .. function:: on_voice_state_update(before, after)
        .. function:: on_member_ban(member)
        .. function:: on_member_unban(server, user)
        .. function:: on_typing(channel, user, when)
        .. function:: on_group_join(channel, user)
    """
    requires_admin = False
    owner_only = False

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

    def create_image_embed(self, url, top_text: str=None, bottom_text: str=None, top_url: str=None,):
        embed = discord.Embed(color=discord.Colour.gold())

        if top_text:
            embed.set_author(name=top_text, url=top_url or url)

        embed.set_image(url=url)

        if bottom_text:
            embed.set_footer(text=bottom_text)

        return embed

    # Events

    async def on_ready(self):
        pass

    async def _on_message(self, message):
        if message.author.id != self.bot.user.id:
            if message.channel.is_private and message.author.id not in OWNER_IDS:
                self.send_message(message.channel, "This bot cannot be used in private messages.")
                return

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

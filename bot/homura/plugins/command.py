import inspect
import logging
import re
from functools import wraps

import discord

from homura.lib.permissions import Permissions
from homura.lib.structure import BackendError, CommandError, Message
from homura.plugins.base import OWNER_IDS

log = logging.getLogger(__name__)


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
                log.debug("prog %s" % prog)
                match = prog.match(message.content)
                log.debug("matching %s" % match)
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

            self.bot.stats.count("command", function=func.__name__)

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
            except CommandError as e:
                embed = discord.Embed(
                    title="Command error",
                    description=str(e),
                    color=discord.Colour.red()
                ).set_thumbnail(
                    url="https://nepeat.github.io/assets/icons/error.png"
                )
                return await self.bot.send_message(message.channel, embed=embed)
            except BackendError as e:
                return await self.bot.send_message(message.channel, str(e))
            except Exception as e:
                embed = discord.Embed(
                    title="Something happened",
                    description="An error happened running this command",
                    color=discord.Colour.red()
                ).set_thumbnail(
                    url="https://nepeat.github.io/assets/icons/error.png"
                )

                # Add the Sentry code if it can be obtained

                sentry_code = await self.bot.on_error("command:" + func.__name__)
                if sentry_code:
                    embed.set_footer(text=sentry_code)

                # Owner extra info

                if author.id in OWNER_IDS:
                    embed.add_field(
                        name="How you fucked up",
                        value=f"```{traceback.format_exc()}```"
                    )

                return await self.bot.send_message(message.channel, embed=embed)

            if response and isinstance(response, Message):
                await self.bot.send_message_object(response, message.channel, message.author, message)

        if usage:
            command_name = "!" + usage
        else:
            command_name = "!" + func.__name__

        wrapper.info = {
            "name": command_name,
            "description": description,
            "permission": permission_name,
            "global": global_command
        }
        wrapper._is_command = True
        wrapper._func = func

        return wrapper
    return actual_decorator

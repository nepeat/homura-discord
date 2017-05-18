# coding=utf-8
import inspect
import logging

import discord

log = logging.getLogger(__name__)
OWNER_IDS = [
    66153853824802816
]


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
        .. function:: on_reaction_add(reaction, use2)
        .. function:: on_guild_emojis_update(guild, before, after)
        .. function:: on_guild_available(guild)
        .. function:: on_voice_state_update(member, before, after)
        .. function:: on_member_ban(guild, member)
        .. function:: on_member_unban(guild, user)
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

    @property
    def loop(self):
        return self.bot.loop

    @property
    def cmd_prefix(self):
        return "!"

    @staticmethod
    def create_image_embed(url, top_text: str=None, bottom_text: str=None, top_url: str=None,):
        embed = discord.Embed(color=discord.Colour.gold())

        if top_text:
            embed.set_author(name=top_text, url=top_url or url)

        embed.set_image(url=url)

        if bottom_text:
            embed.set_footer(text=bottom_text)

        return embed

    @staticmethod
    def get_role(guild, role_idx):
        role_idx = str(role_idx)

        return discord.utils.find(
            lambda role: (
                role.name.strip().lower() == role_idx.strip().lower() or
                str(role.id) == role_idx
            ),
            guild.roles
        )

    # Events

    async def on_ready(self):
        pass

    async def _on_message(self, message):
        if message.author.id != self.bot.user.id:
            if isinstance(message.channel, discord.abc.PrivateChannel) and message.author.id not in OWNER_IDS:
                message.channel.send("This bot cannot be used in private messages.")
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

    async def on_guild_channel_create(self, channel):
        pass

    async def on_guild_channel_update(self, before, after):
        pass

    async def on_guild_channel_delete(self, channel):
        pass

    async def on_private_channel_create(self, channel):
        pass

    async def on_private_channel_update(self, before, after):
        pass

    async def on_private_channel_delete(self, channel):
        pass

    async def on_member_join(self, member):
        pass

    async def on_member_remove(self, member):
        pass

    async def on_member_update(self, before, after):
        pass

    async def on_guild_join(self, guild):
        pass

    async def on_guild_update(self, before, after):
        pass

    async def on_guild_role_create(self, role):
        pass

    async def on_guild_role_delete(self, role):
        pass

    async def on_guild_role_update(self, guild, role):
        pass

    async def on_voice_state_update(self, member, before, after):
        pass

    async def on_member_ban(self, guild, member):
        pass

    async def on_member_unban(self, guild, member):
        pass

    async def on_typing(self, channel, user, when):
        pass

    async def on_logout(self):
        pass

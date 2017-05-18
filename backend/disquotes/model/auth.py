# coding=utf-8
import os
from functools import wraps

from flask import redirect, url_for

from disquotes.lib.cache import redis_cache
from flask_dance.consumer import OAuth2ConsumerBlueprint


def require_login(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not discord.session.authorized:
            return redirect(url_for("oauth-discord.login"))
        return f(*args, **kwargs)
    return inner


@redis_cache.cache_on_arguments("access_token")
def get_servers(access_token):
    return discord.session.get("users/@me/guilds").json()


def get_user_managed_servers(guilds):
    return list(
        filter(
            lambda g: (g['owner'] is True) or
            bool((int(g['permissions']) >> 3) & 1) or  # Manage Server
            bool((int(g['permissions']) >> 5) & 1),    # Administrator
            guilds
        )
    )

discord = OAuth2ConsumerBlueprint(
    "oauth-discord", __name__,
    client_id=os.environ.get("DISCORD_CLIENT_ID"),
    client_secret=os.environ.get("DISCORD_CLIENT_SECRET"),
    base_url="https://discordapp.com/api/",
    token_url="https://discordapp.com/api/oauth2/token",
    authorization_url="https://discordapp.com/api/oauth2/authorize",
    scope=["identify", "guilds"],
)

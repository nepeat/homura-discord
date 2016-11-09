import os
from functools import wraps
from flask_dance.consumer import OAuth2ConsumerBlueprint
from flask import redirect, url_for

def require_login(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not discord.session.authorized:
            return redirect(url_for("oauth-discord.login"))
        return f(*args, **kwargs)
    return inner

discord = OAuth2ConsumerBlueprint(
    "oauth-discord", __name__,
    client_id=os.environ.get("DISCORD_CLIENT_ID"),
    client_secret=os.environ.get("DISCORD_CLIENT_SECRET"),
    base_url="https://discordapp.com/api/",
    token_url="https://discordapp.com/api/oauth2/token",
    authorization_url="https://discordapp.com/api/oauth2/authorize",
    scope=["identify", "guilds"],
)

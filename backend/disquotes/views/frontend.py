from flask import Blueprint, g, request, jsonify, render_template, redirect, url_for
from sqlalchemy.orm.exc import NoResultFound

from disquotes.lib.permissions import Permissions
from disquotes.model.auth import discord, require_login
from disquotes.lib.cache import redis_cache
from disquotes.model import Channel, Event, Server
from disquotes.model.types import EVENT_TYPES

blueprint = Blueprint("frontend", __name__)

@redis_cache.cache_on_arguments("access_token")
def get_servers(session, access_token):
    return session.get("users/@me/guilds").json()

@blueprint.route("/")
@require_login
def front():
    user_servers = get_servers(discord.session, discord.session.access_token)
    quoted_servers = [str(x[0]) for x in g.db.query(Server.server_id).all()]

    return render_template(
        "index.html",
        user_servers=user_servers,
        quoted_servers=quoted_servers
    )

@blueprint.route("/server/<serverid>")
@require_login
def server(serverid=None):
    if not serverid:
        return redirect(url_for("frontend.front"))

    try:
        server = g.db.query(Server).filter(Server.server_id == serverid).one()
    except NoResultFound:
        return redirect(url_for("frontend.front"))

    events = g.db.query(Event).filter(Event.server_id == server.id).order_by(Event.posted.desc()).limit(200).all()

    return render_template(
        "events.html",
        server=server,
        events=events
    )

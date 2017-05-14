# coding=utf-8
from flask import Blueprint, g, redirect, render_template, session, url_for
from sqlalchemy.orm.exc import NoResultFound

from disquotes.model import Event, Server
from disquotes.model.auth import get_servers, get_user_managed_servers, require_login

blueprint = Blueprint("frontend", __name__)


@blueprint.before_request
def before_app():
    if "oauth-discord_oauth_token" in session:
        g.session_token = session["oauth-discord_oauth_token"]["access_token"]
        g.servers = get_servers(g.session_token)


@blueprint.route("/")
@require_login
def front():
    user_servers = get_user_managed_servers(g.servers)
    quoted_servers = [str(x[0]) for x in g.db.query(Server.server_id).all()]

    return render_template(
        "index.html",
        user_servers=user_servers,
        quoted_servers=quoted_servers
    )


@blueprint.route("/server/<serverid>/deleted")
@require_login
def deleted_messages(serverid=None):
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

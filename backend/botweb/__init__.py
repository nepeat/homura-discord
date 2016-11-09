# This Python file uses the following encoding: utf-8
import os

from flask import Flask, g, jsonify, request
from sqlalchemy.orm.exc import NoResultFound

from botweb.model import Channel, Event, Server
from botweb.model.handlers import (before_request, connect_redis, connect_sql,
                                   disconnect_redis, disconnect_sql)

app = Flask(__name__)

# Debug

app.config['PROPAGATE_EXCEPTIONS'] = True

if 'DEBUG' in os.environ:
    app.config['DEBUG'] = True

# Handlers

app.before_request(connect_sql)
app.before_request(connect_redis)
app.before_request(before_request)
app.teardown_request(disconnect_sql)
app.teardown_request(disconnect_redis)

# Validators

def validate_push(form):
    missing = [x for x in ["server", "channel", "data", "type"] if x not in form]
    if missing:
        return {"missing": missing}

    if form["type"] not in [
        "delete",
        "edit",
        "join",
        "edit"
    ]:
        return {"type": "invalid"}

    return None

# Creators

def get_server_channel(server_id, channel_id=None):
    try:
        server = g.db.query(Server).filter(Server.server == server_id).one()
    except NoResultFound:
        server = Server(
            server=server_id
        )
        g.db.add(server)
        g.db.commit()

    if not channel_id:
        return server, None

    try:
        channel = g.db.query(Channel).filter(
            Channel.server == server.id
        ).filter(
            Channel.channel == channel_id
        ).one()
    except NoResultFound:
        channel = Channel(
            server=server.id,
            channel=channel_id
        )
        g.db.add(channel)
        g.db.commit()

    return server, channel

def create_event(event_type, server, channel=None, data={}):
    event = Event(
        type=event_type,
        server=server.id,
        channel=channel.id if channel else None,
        data=data
    )
    g.db.add(event)
    g.db.commit()

# Routes

@app.route("/")
def home():
    return "ok"

@app.route("/push/event", methods=["GET", "POST"])
def push_delete():
    invalid = validate_push(request.json)
    if invalid:
        return jsonify({
            "status": "error",
            "error": invalid
        }), 503

    server, channel = get_server_channel(request.json["server"], request.json["channel"])
    create_event(request.json["type"], server, channel, request.json["data"])

    return jsonify({"status": "ok"})
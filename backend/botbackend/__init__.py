# This Python file uses the following encoding: utf-8
import os
import logging

from flask import Flask, g, jsonify, request
from raven.contrib.flask import Sentry
from sqlalchemy.orm.exc import NoResultFound

from botbackend.model import Channel, Event, Server
from botbackend.model.types import EVENT_TYPES
from botbackend.model.handlers import (before_request, connect_redis, connect_sql,
                                   disconnect_redis, disconnect_sql)

app = Flask(__name__)

# Debug
app.config['PROPAGATE_EXCEPTIONS'] = True

if 'DEBUG' in os.environ:
    app.config['DEBUG'] = True

app.config["SENTRY_INCLUDE_PATHS"] = ["botbackend"]
sentry = Sentry(
    app,
    dsn=app.config.get("SENTRY_DSN", None),
    logging=True,
    level=logging.ERROR,
)

# Handlers

app.before_request(connect_sql)
app.before_request(connect_redis)
app.before_request(before_request)
app.teardown_request(disconnect_sql)
app.teardown_request(disconnect_redis)

# Validators

def validate_push(form):
    try:
        msg_type = form["type"].decode("utf-8")
    except:
        msg_type = form["type"]

    missing = [x for x in ["server", "channel", "data", "type"] if x not in form]
    if missing:
        return {"missing": missing}

    if msg_type not in EVENT_TYPES:
        return {"type": "invalid:%s" % (form["type"])}

    return None

# Creators

def get_server_channel(server_id, channel_id=None, create=False):
    if not server_id:
        return None, None

    try:
        server = g.db.query(Server).filter(Server.server == server_id).one()
    except NoResultFound:
        server = None
        if create:
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
        channel = None
        if create:
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

@app.route("/events/<type>", methods=["GET"])
def event_get(type=None):
    if type not in EVENT_TYPES:
        return jsonify({"state": "badtype"})

    query = g.db.query(Event).filter(Event.type == type).order_by(Event.posted)

    server, channel = get_server_channel(request.args.get("server"), request.args.get("channel"), create=False)
    if server:
        query = query.filter(Event.server == server.id)

    if channel:
        query = query.filter(Event.channel == channel.id)

    return jsonify({
        "events": [_.to_dict() for _ in query.limit(10).all()]
    })

@app.route("/events/push", methods=["GET", "POST"])
def event_post():
    invalid = validate_push(request.json)
    if invalid:
        return jsonify({
            "status": "error",
            "error": invalid
        }), 503

    server, channel = get_server_channel(request.json["server"], request.json["channel"], create=True)
    create_event(request.json["type"], server, channel, request.json["data"])

    return jsonify({"status": "ok"})

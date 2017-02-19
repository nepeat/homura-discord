import json

from flask import g, request
from flask_restplus import Namespace, Resource, abort, fields
from sqlalchemy.orm.exc import NoResultFound

from disquotes.model import Channel, Event, Permission, Server
from disquotes.model.types import EVENT_TYPES
from disquotes.model.validators import validate_push
from disquotes.views.api.base import ResourceBase

ns = Namespace("events", "Server eventlog")

event_model = ns.model("Event", {
    "type": fields.String,
    "data": fields.Raw
})

events_model = ns.model("Events", {
    "events": fields.Nested(event_model)
})


@ns.route("/bulk")
class BulkEventsResource(ResourceBase):
    @ns.param("data", "JSON mapping of server ids to server names")
    def put(self):
        data = self.get_field("data", asjson=True)

        for server_id, server_name in data.items():
            server, channel = self.get_server_channel(create=True, server=server_id)
            server.name = server_name
            g.db.flush()

@ns.route("/<event_type>")
class EventsResource(ResourceBase):
    @ns.param("server", "Discord Server ID", type=int, required=True)
    @ns.param("channel", "Discord Channel ID", type=int)
    @ns.param("before", "Get events before this ID", type=int)
    @ns.param("limit", "Maximum events returned (1-200)", type=int)
    @ns.marshal_with(events_model)
    def get(self, event_type):
        limit = request.args.get("limit", 5)
        try:
            limit = int(limit)
            if limit < 1 or limit > 200:
                raise ValueError()
        except (ValueError, TypeError):
            limit = 5

        before = request.args.get("before", None)
        try:
            before = int(before)
        except (ValueError, TypeError):
            before = None

        if event_type != "all" and event_type not in EVENT_TYPES:
            abort(400, f"Invalid event type specified. You have inputted `{event_type}`")

        query = g.db.query(Event)

        if event_type != "all":
            query = query.filter(Event.type == event_type)

        server, channel = self.get_server_channel(create=False)
        if server:
            query = query.filter(Event.server_id == server.id)

        if channel:
            query = query.filter(Event.channel_id == channel.id)

        if "channel" in request.args and not channel:
            return {
                "events": []
            }

        if before:
            query = query.filter(Event.id < before)

        return {
            "events": [_ for _ in query.order_by(Event.posted.desc()).limit(limit).all()][::-1]
        }

    @ns.param("server", "Discord Server ID", _in="formData", type=int, required=True)
    @ns.param("channel", "Discord Channel ID", _in="formData", type=int)
    @ns.param("data", "Event payload", _in="formData", required=True)
    def put(self, event_type):
        invalid = validate_push(request, event_type)
        if invalid:
            abort(400, "Invalid event payload.", description=invalid)

        server, channel = self.get_server_channel(create=True)

        data = self.get_field("data", asjson=True)

        event = Event(
            type=event_type,
            server_id=server.id,
            channel_id=channel.id if channel else None,
            data=data
        )
        g.db.add(event)

        if event_type == "rename_channel" and channel:
            channel.name = data["channel"]["after"]
        elif event_type == "rename_server" and server:
            server.name = data["server"]["after"]

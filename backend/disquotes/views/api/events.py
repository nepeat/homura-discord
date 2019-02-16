# coding=utf-8

import datetime

from flask import g, request
from flask_restplus import Namespace, abort, fields
from sqlalchemy.dialects.postgresql import insert

from disquotes.model import Event, Message
from disquotes.model.types import EVENT_TYPES
from disquotes.model.validators import validate_push
from disquotes.views.api.base import ResourceBase

ns = Namespace("events", "Server eventlog")

event_model = ns.model("Event", {
    "type": fields.String,
    "data": fields.Raw
})

events_model = ns.model("Events", {
    "events": fields.List(fields.Nested(event_model))
})


@ns.route("/bulk")
class BulkEventsResource(ResourceBase):
    @ns.param("data", "JSON mapping of server ids to server names")
    def put(self):
        data = self.get_field("data", asjson=True)

        for server_id, server_data in data.items():
            server, channel = self.get_server_channel(create=True, server=server_id)

            if "name" in server_data:
                server.name = server_data["name"]

            for channel_id, channel_name in server_data["channels"].items():
                _, channel = self.get_server_channel(create=True, server=server_id, channel=channel_id)
                channel.name = channel_name

            g.db.flush()


@ns.route("/bulk_channel")
class BulkChannelResource(ResourceBase):
    @ns.param("data", "JSON list of many messages")
    def put(self):
        data = self.get_field("data", asjson=True)

        server_cache = {}
        channel_cache = {}

        for message in data:
            server_id = message["server_id"]
            channel_id = message["channel_id"]

            created_time = message.get("created")
            edited_time = message.get("edited")

            if server_id not in server_cache or channel_id not in channel_cache:
                server, channel = self.get_server_channel(create=True, server=server_id, channel=channel_id)
                server_cache[server_id] = server
                channel_cache[channel_id] = channel
            else:
                server = server_cache[server_id]
                channel = channel_cache[channel_id]

            data = dict(
                message_id=message["id"],
                server_id=server.id,
                channel_id=channel.id,
                author_id=message["author_id"],
                tts=message.get("tts", False),
                pinned=message["pinned"],
                attachments=message["attachments"],
                reactions=message.get("reactions", []),
                embeds=message.get("embeds", []),
                message=message["message"]
            )

            if created_time:
                data["created"] = datetime.datetime.utcfromtimestamp(created_time)

            if edited_time:
                data["edited"] = datetime.datetime.utcfromtimestamp(edited_time)

            new_statement = insert(Message).values(**data).on_conflict_do_update(index_elements=["message_id"], set_=data)
            g.db.execute(new_statement)


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
        elif event_type == "rename_guild" and server:
            server.name = data["server"]["after"]
        elif event_type == "guild_join" and server:
            server.name = data["server"]["name"]

# coding=utf-8
import json

from flask import g, request
from flask_restplus import Resource, abort

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.exc import NoResultFound

from disquotes.model import Channel, Server


class ResourceBase(Resource):
    def get_field(self, field: str, default=None, asjson: bool=False):
        if request.is_json and field in request.json:
            return request.json.get(field, default)
        elif request.form and field in request.form:
            content = request.form.get(field, default)
        elif request.args and field in request.args:
            content = request.args.get(field, default)
        else:
            content = None

        if not content:
            return default

        if asjson:
            return json.loads(content)

        return content

    def get_server_channel(self, create=False, **kwargs) -> (Server, Channel):
        server_id = int(kwargs.get("server", self.get_field("server", 0)))
        if server_id == 0:
            abort(400, "Server ID field is blank.")

        try:
            channel_id = int(kwargs.get("channel", self.get_field("channel", 0)))
        except (TypeError, ValueError):
            channel_id = None

        try:
            server = g.db.query(Server).filter(Server.server_id == server_id).one()
        except NoResultFound:
            server = None
            if create:
                new_statement = insert(Server).values(
                    server_id=server_id
                ).on_conflict_do_nothing(index_elements=["server_id"])
                g.db.execute(new_statement)
                g.db.commit()
                server = g.db.query(Server).filter(Server.server_id == server_id).one()
            else:
                abort(400, "A server object could not be found.")

        if not channel_id:
            return server, None

        try:
            channel = g.db.query(Channel).filter(
                Channel.server_id == server.id
            ).filter(
                Channel.channel_id == channel_id
            ).one()
        except NoResultFound:
            channel = None
            if create:
                new_statement = insert(Channel).values(
                    server_id=server.id,
                    channel_id=channel_id
                ).on_conflict_do_nothing(index_elements=["channel_id"])
                g.db.execute(new_statement)
                g.db.commit()
                channel = g.db.query(Channel).filter(
                    Channel.server_id == server.id
                ).filter(
                    Channel.channel_id == channel_id
                ).one()

        return server, channel

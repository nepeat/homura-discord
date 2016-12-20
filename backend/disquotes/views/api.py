from flask import Blueprint, g, request, jsonify, request
from flask_restplus import Resource, Api, abort
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import DataError

from sqlalchemy import or_
from disquotes.model import Channel, Event, Server, Channel, Permission
from disquotes.model.validators import validate_push
from disquotes.model.types import EVENT_TYPES

blueprint = Blueprint("api", __name__)
api = Api(blueprint)

@api.errorhandler
def default_error_handler(error):
    '''Default error handler'''
    return {
        'message': str(error)
    }, getattr(error, 'code', 500)


@api.route("/permissions")
@api.param("server", "Discord Server ID", type=int, required=True)
@api.param("channel", "Discord Channel ID", type=int)
class PermissionResource(Resource):
    def get_server_channel(self) -> (Server, Channel):
        server_id = int(request.args.get("server", 0))
        channel_id = int(request.args.get("channel", 0))

        try:
            server = g.db.query(Server).filter(Server.server_id == server_id).one()
        except (NoResultFound, DataError):
            abort(400, "A server object could not be found.")

        try:
            channel = g.db.query(Channel).filter(Channel.channel_id == channel_id).one()
        except (NoResultFound, DataError):
            return server, None

        return (server, channel)

    def get(self):
        server, channel = self.get_server_channel()

        if channel:
            query = g.db.query(Permission).filter(or_(
                Permission.server_id == server.id,
                Permission.channel_id == channel.id
            ))
        else:
            query = g.db.query(Permission).filter(
                Permission.server_id == server.id
            )

        return query.all()

    def put(self):
        server, channel = self.get_server_channel()

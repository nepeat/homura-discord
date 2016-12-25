from flask import Blueprint, g, request, jsonify, request
from flask_restplus import Resource, Api, abort, fields
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import DataError

from sqlalchemy import or_
from disquotes.model import Channel, Event, Server, Channel, Permission
from disquotes.model.validators import validate_push
from disquotes.model.types import EVENT_TYPES
from disquotes.views.api import permissions, events

blueprint = Blueprint("api", __name__)
api = Api(
    blueprint,
    version="lol",
    title="Internal Bot API",
    description="API services used by the bot"
)

@api.errorhandler
def default_error_handler(error):
    """Default error handler"""
    return {
        'message': str(error)
    }, getattr(error, 'code', 500)


api.add_namespace(permissions.ns)
api.add_namespace(events.ns)

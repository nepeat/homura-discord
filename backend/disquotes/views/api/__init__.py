from flask import Blueprint, g, jsonify, request
from flask_restplus import Api, Resource, abort, fields
from sqlalchemy import or_
from sqlalchemy.exc import DataError
from sqlalchemy.orm.exc import NoResultFound

from disquotes.model import Channel, Event, Permission, Server
from disquotes.model.types import EVENT_TYPES
from disquotes.model.validators import validate_push
from disquotes.views.api import events, permissions, settings

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
api.add_namespace(settings.ns)

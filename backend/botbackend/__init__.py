# This Python file uses the following encoding: utf-8
import os
import logging

from flask import Flask
from raven.contrib.flask import Sentry

from botbackend.model.handlers import (before_request, connect_redis, connect_sql,
                                   disconnect_redis, disconnect_sql)
from botbackend.views import events

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

# Routes

@app.route("/")
def home():
    return "ok"

app.register_blueprint(events.blueprint, url_prefix="/events")

# This Python file uses the following encoding: utf-8
import os
import logging

from flask import Flask
from raven.contrib.flask import Sentry

from disquotes.model.auth import discord
from disquotes.model.handlers import (before_request, connect_redis, connect_sql,
                                   commit_sql, disconnect_redis, disconnect_sql)
from disquotes.views import api, frontend

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", os.environ.get("SECRET_KEY"))
app.config["SESSION_COOKIE_NAME"] = "disquotes"

# Debug
app.config["PROPAGATE_EXCEPTIONS"] = True

if "DEBUG" in os.environ:
    app.config["DEBUG"] = True

if app.debug:
    app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SENTRY_INCLUDE_PATHS"] = ["disquotes"]
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
app.after_request(commit_sql)
app.teardown_request(disconnect_sql)
app.teardown_request(disconnect_redis)

# Routes

app.register_blueprint(frontend.blueprint)
app.register_blueprint(discord, url_prefix="/auth")
app.register_blueprint(api.blueprint, url_prefix="/api")

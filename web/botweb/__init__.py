# This Python file uses the following encoding: utf-8
import os
import traceback

from botbackend.lib.extensions import inject_extensions
from botbackend.model.handlers import (before_request, cache_breaker,
                                  connect_redis,
                                   connect_sql, disconnect_redis,
                                   disconnect_sql, set_cookie)
from archives.views import archive, graph
from flask import Flask, render_template, request

app = Flask(__name__)

# Throw tracebacks to console
app.config['PROPAGATE_EXCEPTIONS'] = True

if 'DEBUG' in os.environ:
    app.config['DEBUG'] = True

# Inject Jinja defaults
inject_extensions(app)

# Cache breaking
app.url_defaults(cache_breaker)

# Request handlers
app.before_request(connect_sql)
app.before_request(connect_redis)
app.before_request(before_request)
app.after_request(set_cookie)
app.teardown_request(disconnect_sql)
app.teardown_request(disconnect_redis)

# Blueprints
app.register_blueprint(archive.blueprint)
app.register_blueprint(graph.blueprint, url_prefix="/graph")

# Error handlers
@app.errorhandler(404)
def notfound_error(e):
    return render_template("errors/404.html"), 404

if not app.config['DEBUG']:
    @app.errorhandler(Exception)
    def production_error(e):
        if request.is_xhr:
            if 'debug' not in request.args and 'debug' not in request.form:
                raise

        traceback.print_exc()

        return render_template(
            "errors/exception.html",
            traceback=traceback.format_exc()
        ), 500

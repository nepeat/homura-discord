# This Python file uses the following encoding: utf-8
import os

from flask import g, request
from redis import ConnectionPool, StrictRedis

from disquotes.model import sm

redis_pool = ConnectionPool(
    host=os.environ.get('REDIS_PORT_6379_TCP_ADDR', os.environ.get('REDIS_HOST', '127.0.0.1')),
    port=int(os.environ.get('REDIS_PORT_6379_TCP_PORT', os.environ.get('REDIS_PORT', 6379))),
    db=int(os.environ.get('REDIS_DB', 0)),
    decode_responses=True
)

def set_cookie(response):
    if "archives" not in request.cookies and hasattr(g, "session_id"):
        response.set_cookie(
            "archives",
            g.session_id,
            max_age=365 * 24 * 60 * 60,
            httponly=True,
        )
    return response

def connect_sql():
    g.db = sm()

def connect_redis():
    g.redis = StrictRedis(connection_pool=redis_pool)

def before_request():
    pass

def commit_sql(response=None):
    # Don't commit on 4xx and 5xx.
    if response is not None and response.status[0] not in {"2", "3"}:
        g.db.rollback()
        return response
    if hasattr(g, "db"):
        g.db.commit()
    return response

def disconnect_sql(result=None):
    if hasattr(g, "db"):
        g.db.close()
        del g.db

    return result

def disconnect_redis(result=None):
    if hasattr(g, "redis"):
        del g.redis

    return result

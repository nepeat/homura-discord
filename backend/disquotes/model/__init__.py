# This Python file uses the following encoding: utf-8
import datetime
import os

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Unicode, create_engine
from sqlalchemy.dialects.postgresql import JSONB, HSTORE
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, validates
from sqlalchemy.schema import Index
from sqlalchemy.ext.mutable import MutableDict

from disquotes.model.types import EVENT_TYPES

debug = os.environ.get('DEBUG', False)

engine = create_engine(os.environ["POSTGRES_URL"], convert_unicode=True, pool_recycle=3600)

if debug:
    engine.echo = True

sm = sessionmaker(autocommit=False,
                  autoflush=False,
                  bind=engine)

base_session = scoped_session(sm)

Base = declarative_base()
Base.query = base_session.query_property()


def now():
    return datetime.datetime.now()


class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger, nullable=False)

    name = Column(Unicode(100))
    meta = Column(JSONB)


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    server_id = Column(ForeignKey("servers.id"), nullable=False)
    name = Column(Unicode(100))
    server = relationship("Server")

    meta = Column(JSONB)


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    server_id = Column(ForeignKey("servers.id"), nullable=False)
    channel_id = Column(ForeignKey("channels.id"))
    posted = Column(DateTime(), nullable=False, default=now)

    type = Column(String(32), nullable=False)
    data = Column(JSONB, nullable=False)

    server = relationship("Server")
    channel = relationship("Channel")

    def to_dict(self):
        return self.data if self.data else {}

    @validates("type")
    def validate_type(self, _key, event_type):
        assert event_type in EVENT_TYPES
        return event_type


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    server_id = Column(ForeignKey("servers.id"), nullable=False)
    channel_id = Column(ForeignKey("channels.id"))
    permission = Column(String, nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    server_id = Column(ForeignKey("servers.id"), nullable=False)
    store = Column(MutableDict.as_mutable(HSTORE))


Index("permission_server", Permission.server_id)

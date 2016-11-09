# This Python file uses the following encoding: utf-8
import datetime
import os

from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        String, Unicode, create_engine)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, validates
from sqlalchemy.schema import Index

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

    meta = Column(JSONB)

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    server_id = Column(ForeignKey("servers.id"), nullable=False)

    meta = Column(JSONB)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    server_id = Column(ForeignKey("servers.id"), nullable=False)
    channel_id = Column(ForeignKey("channels.id"))
    posted = Column(DateTime(), nullable=False, default=now)

    type = Column(String(32), nullable=False)
    data = Column(JSONB, nullable=False)

    def to_dict(self):
        return self.data if self.data else {}

    @validates("type")
    def validate_type(self, key, type):
        assert type in EVENT_TYPES
        return type

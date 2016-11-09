# This Python file uses the following encoding: utf-8
import datetime
import os

from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, Integer,
                        String, Unicode, create_engine)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, validates
from sqlalchemy.schema import Index

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
    server = Column(BigInteger, nullable=False)

    meta = Column(JSONB)

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    server = Column(ForeignKey("servers.id"), nullable=False)
    channel = Column(BigInteger, nullable=False)

    meta = Column(JSONB)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    server = Column(ForeignKey("servers.id"), nullable=False)
    channel = Column(ForeignKey("channels.id"))
    posted = Column(DateTime(), nullable=False, default=now)

    type = Column(String(32), nullable=False)
    data = Column(JSONB, nullable=False)

    @validates("type")
    def validate_type(self, key, type):
        assert type in [
            "edit",
            "delete",
            "join",
            "leave"
        ]

        return type

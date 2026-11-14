"""SQLAlchemy engine/session helpers."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def create_db_engine(database_url: str) -> Engine:
    """Create an engine; SQLite is shared across threadpool workers."""
    return create_engine(database_url, connect_args={"check_same_thread": False})


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create all tables (import models first so they register on `Base`)."""
    from app.models import conversation, dataset  # noqa: F401

    Base.metadata.create_all(engine)

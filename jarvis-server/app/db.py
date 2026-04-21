import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings
from app.services.runtime_config_service import get_database_url


class Base(DeclarativeBase):
    pass


_database_url_override: str | None = None
_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def _build_engine(database_url: str) -> Engine:
    engine_kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)
    event.listen(engine, "connect", _set_sqlite_pragma)
    return engine


def _get_database_url() -> str:
    return _database_url_override or get_database_url() or get_settings().database_url


def get_database_url_for_runtime() -> str:
    return _get_database_url()


def configure_database(database_url: str) -> None:
    global _database_url_override
    _database_url_override = database_url
    _dispose_database_objects()


def reset_database() -> None:
    global _database_url_override
    _database_url_override = None
    _dispose_database_objects()


def _dispose_database_objects() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(_get_database_url())
    return _engine


def SessionLocal():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _session_factory()


def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

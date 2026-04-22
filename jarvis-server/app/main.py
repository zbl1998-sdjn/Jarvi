from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.routers.assistant import router as assistant_router
from app.db import Base, get_engine
from app.models import MemoryFact, SessionArtifact, UserProfileFact
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.proactive import router as proactive_router
from app.routers.realtime import router as realtime_router
from app.routers.telemetry import router as telemetry_router
from app.routers.tts import router as tts_router
from app.services.proactive_service import get_daemon

APP_MODE = "m6"


def _apply_lightweight_migrations(engine) -> None:
    """Add new columns that appeared after initial create_all runs.

    SQLAlchemy's create_all never alters existing tables, so we patch the
    few additive columns we've introduced since the original schema.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {
        "memory_facts": MemoryFact.__table__,
        "user_profile_facts": UserProfileFact.__table__,
        "session_artifacts": SessionArtifact.__table__,
    }
    for name, table in required_tables.items():
        if name not in existing_tables:
            table.create(bind=engine)
    if "chat_sessions" not in existing_tables:
        return
    existing = {col["name"] for col in inspector.get_columns("chat_sessions")}
    if "title" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(255)"))


def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis Server")
    app.state.mode = APP_MODE
    app.state.database_ready = True
    app.state.database_error = ""

    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        _apply_lightweight_migrations(engine)
    except Exception as error:
        app.state.database_ready = False
        app.state.database_error = str(error)

    app.include_router(health_router)
    app.include_router(assistant_router)
    app.include_router(chat_router)
    app.include_router(realtime_router)
    app.include_router(proactive_router)
    app.include_router(telemetry_router)
    app.include_router(tts_router)

    @app.on_event("startup")
    async def _start_proactive_daemon() -> None:
        get_daemon().start()

    @app.on_event("shutdown")
    async def _stop_proactive_daemon() -> None:
        await get_daemon().stop()

    return app

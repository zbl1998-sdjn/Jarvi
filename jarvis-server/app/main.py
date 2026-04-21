from fastapi import FastAPI

from app.routers.assistant import router as assistant_router
from app.db import Base, get_engine
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.realtime import router as realtime_router

APP_MODE = "m6"


def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis Server")
    app.state.mode = APP_MODE
    app.state.database_ready = True
    app.state.database_error = ""

    try:
        Base.metadata.create_all(bind=get_engine())
    except Exception as error:
        app.state.database_ready = False
        app.state.database_error = str(error)

    app.include_router(health_router)
    app.include_router(assistant_router)
    app.include_router(chat_router)
    app.include_router(realtime_router)
    return app

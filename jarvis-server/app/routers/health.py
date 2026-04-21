from fastapi import APIRouter, Request
from sqlalchemy import text

from app.db import SessionLocal, get_database_url_for_runtime
from app.services.runtime_config_service import (
    check_database_connection,
    check_llm_connection,
    check_speech_configuration,
    get_active_provider,
    get_speech_config,
)

router = APIRouter()


@router.get("/api/health")
async def health(request: Request) -> dict[str, object]:
    database_ready = bool(getattr(request.app.state, "database_ready", True))
    database_status = (
        check_database_connection(get_database_url_for_runtime()) if database_ready else "offline"
    )
    llm_status = check_llm_connection(get_active_provider())
    speech_status = check_speech_configuration(get_speech_config())
    config_status = "ready" if llm_status != "missing" or speech_status != "missing" else "missing"

    if database_ready and database_status == "ready":
        try:
            with SessionLocal() as db:
                db.execute(text("select 1"))
                db.rollback()
        except Exception:
            database_status = "offline"
            database_ready = False
    else:
        database_ready = False

    return {
        "ok": database_ready,
        "service": "jarvis-server",
        "mode": getattr(request.app.state, "mode", "m1"),
        "degraded": not database_ready,
        "dependencies": {
            "database": database_status,
            "llm": llm_status,
            "speech": speech_status,
            "config": config_status,
        },
    }

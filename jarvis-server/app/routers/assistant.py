import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db import SessionLocal, configure_database
from app.services.action_service import ActionService
from app.services.memory_service import MemoryService
from app.services.multimodal_service import MultimodalService
from app.services.permission_service import PermissionService
from app.services.runtime_config_service import (
    check_database_connection,
    check_llm_connection,
    check_speech_configuration,
    get_runtime_config,
    save_runtime_config,
)
from app.services.search_service import SearchService
from app.services.summary_service import SummaryService
from app.services.wakeword_service import WakewordService

router = APIRouter()

logger = logging.getLogger(__name__)

wakeword_service = WakewordService()
search_service = SearchService()
summary_service = SummaryService()
permission_service = PermissionService()
action_service = ActionService(permission_service)
memory_service = MemoryService()
multimodal_service = MultimodalService()


class InterpretRequest(BaseModel):
    text: str
    hotkey_armed: bool = False


class SummaryRequest(BaseModel):
    source_type: str
    content: str


class TaskRequest(BaseModel):
    title: str
    detail: str = ""


class ActionRequest(BaseModel):
    action_type: str
    target: str
    content: str | None = None
    approved: bool = False


class PreferenceRequest(BaseModel):
    teacher_style: str
    voice_name: str


class ContextUploadRequest(BaseModel):
    title: str
    source_type: str
    content: str


class WorkspaceStateRequest(BaseModel):
    workspace: str
    session_id: str | None = None


class ProviderRequest(BaseModel):
    id: str
    label: str
    base_url: str
    api_key: str
    model: str
    enabled: bool = True


class SpeechConfigRequest(BaseModel):
    api_key: str = ""
    asr_model: str = "paraformer-realtime-v2"
    tts_model: str = "cosyvoice-v1"
    voice_name: str = "longxiaochun"
    language: str = "zh-CN"
    provider: str = "aliyun"


class RuntimeConfigRequest(BaseModel):
    database_url: str
    providers: list[ProviderRequest]
    active_provider_id: str
    speech: SpeechConfigRequest
    knowledge_root: str = ""


@router.post("/api/assistant/interpret")
def interpret_voice(request: InterpretRequest) -> dict[str, object]:
    interpretation = wakeword_service.interpret(
        request.text,
        hotkey_armed=request.hotkey_armed,
    )
    return interpretation.to_dict()


@router.get("/api/search")
def search(query: str, scope: str = "local") -> dict[str, object]:
    db = SessionLocal()
    try:
        if scope in {"search", "local", "knowledge", "web", "auto"}:
            memory_service.update_workspace_state(db, active_workspace="search")
        db.commit()
        return {
            "results": [result.to_dict() for result in search_service.search(query, scope)],
        }
    finally:
        db.close()


@router.post("/api/summary")
def summarize(request: SummaryRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        result = summary_service.summarize(request.source_type, request.content)
        memory_service.remember(
            db,
            kind="summary",
            content=result["summary"],
            source=request.source_type,
        )
        memory_service.update_workspace_state(db, active_workspace="summary")
        db.commit()
        return result
    finally:
        db.close()


@router.post("/api/tasks")
def create_task(request: TaskRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        task = memory_service.create_task(db, request.title, request.detail)
        memory_service.update_workspace_state(db, active_workspace="tasks")
        db.commit()
        return {
            "id": task.id,
            "title": task.title,
            "detail": task.detail,
            "status": task.status,
            "stage": task.stage,
        }
    finally:
        db.close()


@router.post("/api/actions/propose")
def propose_action(request: ActionRequest) -> dict[str, object]:
    return action_service.propose(request.action_type, request.target).to_dict()


@router.post("/api/actions/execute")
def execute_action(request: ActionRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        result = action_service.execute(
            db,
            request.action_type,
            request.target,
            content=request.content,
            approved=request.approved,
        )
        memory_service.remember(
            db,
            kind="action",
            content=f"{result.action_type}:{result.target}:{result.status}",
            source="actions",
        )
        memory_service.update_workspace_state(db, active_workspace="records")
        db.commit()
        return result.to_dict()
    finally:
        db.close()


@router.get("/api/preferences")
def get_preferences() -> dict[str, object]:
    db = SessionLocal()
    try:
        preference = memory_service.get_preferences(db)
        db.commit()
        return {
            "teacher_style": preference.teacher_style,
            "voice_name": preference.voice_name,
        }
    finally:
        db.close()


@router.get("/api/runtime-config")
def load_runtime_configuration() -> dict[str, object]:
    return get_runtime_config().to_dict()


@router.post("/api/runtime-config")
def store_runtime_configuration(request: RuntimeConfigRequest) -> dict[str, object]:
    runtime_config = save_runtime_config(request.model_dump())
    # Reconfigure the database first so voice sync targets the newly configured DB,
    # and so a voice-sync error can never prevent the DB from being switched.
    configure_database(runtime_config.database_url)
    # Sync the DB-backed preference voice_name to the new DB.
    # This is non-fatal: if it fails, the database reconfiguration already completed.
    if request.speech.voice_name:
        db = SessionLocal()
        try:
            current = memory_service.get_preferences(db)
            memory_service.update_preferences(
                db,
                teacher_style=current.teacher_style,
                voice_name=request.speech.voice_name,
            )
            db.commit()
        except Exception as exc:
            logger.warning("Voice sync after runtime-config save failed: %s", exc)
        finally:
            db.close()
    return runtime_config.to_dict()


@router.post("/api/runtime-config/check")
def validate_runtime_configuration() -> dict[str, object]:
    runtime_config = get_runtime_config()
    database_status = check_database_connection(runtime_config.database_url)
    llm_status = check_llm_connection(
        next(
            (
                provider
                for provider in runtime_config.providers
                if provider.id == runtime_config.active_provider_id
            ),
            runtime_config.providers[0],
        )
    )
    speech_status = check_speech_configuration(runtime_config.speech)
    return {
        "active_provider_id": runtime_config.active_provider_id,
        "dependencies": {
            "database": database_status,
            "llm": llm_status,
            "speech": speech_status,
            "config": "ready"
            if runtime_config.providers and runtime_config.database_url.strip()
            else "missing",
        },
    }


@router.post("/api/preferences")
def save_preferences(request: PreferenceRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        preference = memory_service.update_preferences(
            db,
            teacher_style=request.teacher_style,
            voice_name=request.voice_name,
        )
        db.commit()
        teacher_style = preference.teacher_style
        voice_name = preference.voice_name
    finally:
        db.close()
    # Mirror the new voice_name into the runtime config JSON so GET /api/runtime-config
    # stays consistent with preferences (bidirectional Task 6 fix).
    if request.voice_name:
        current_config = get_runtime_config()
        config_dict = current_config.to_dict()
        config_dict["speech"]["voice_name"] = request.voice_name
        save_runtime_config(config_dict)
    return {
        "teacher_style": teacher_style,
        "voice_name": voice_name,
    }


@router.post("/api/context/upload")
def upload_context(request: ContextUploadRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        result = multimodal_service.ingest_context(
            db,
            title=request.title,
            source_type=request.source_type,
            content=request.content,
        )
        memory_service.update_workspace_state(db, active_workspace="search")
        db.commit()
        return result
    finally:
        db.close()


@router.post("/api/workspace/state")
def save_workspace_state(request: WorkspaceStateRequest) -> dict[str, object]:
    db = SessionLocal()
    try:
        state = memory_service.update_workspace_state(
            db,
            active_workspace=request.workspace,
            session_id=request.session_id,
        )
        db.commit()
        return {
            "workspace": state.active_workspace,
            "session_id": state.last_session_id,
        }
    finally:
        db.close()


@router.get("/api/home")
def home() -> dict[str, object]:
    db = SessionLocal()
    try:
        snapshot = memory_service.snapshot(db)
        runtime_config = get_runtime_config()
        active_provider = next(
            (p for p in runtime_config.providers if p.id == runtime_config.active_provider_id),
            runtime_config.providers[0],
        )
        knowledge_root_str = runtime_config.knowledge_root or get_settings().knowledge_root
        knowledge_root = Path(knowledge_root_str)
        snapshot["runtime"] = {
            "llm_provider": active_provider.id,
            "llm_model": active_provider.model,
            "speech_provider": runtime_config.speech.provider,
            # Reflect the DB-backed effective preference so runtime.voice_name
            # always matches the voice that /api/tts actually uses, preventing
            # drift with the runtime config JSON.
            "voice_name": snapshot["preferences"]["voice_name"],
            "knowledge_root": str(knowledge_root),
            "knowledge_root_exists": knowledge_root.exists(),
        }
        return snapshot
    finally:
        db.close()

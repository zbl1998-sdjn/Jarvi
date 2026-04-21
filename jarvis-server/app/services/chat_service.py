import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
import inspect

from app.config import get_settings
from app.repositories.session_repository import SessionRepository
from app.services.knowledge_context_service import KnowledgeContextService
from app.services.kimi_client import KimiChatClient
from app.services.memory_service import MemoryService
from app.services.runtime_config_service import get_active_provider


def sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@dataclass(frozen=True)
class PreparedChat:
    session_id: str
    answer: str


def create_chat_client() -> KimiChatClient:
    settings = get_settings()
    provider = get_active_provider()
    return KimiChatClient(
        api_key=provider.api_key or settings.kimi_api_key,
        base_url=provider.base_url or settings.kimi_base_url,
        model=provider.model or settings.kimi_model,
        timeout_seconds=settings.kimi_timeout_seconds,
        system_prompt=settings.kimi_system_prompt,
    )


def prepare_chat(
    query: str,
    repository: SessionRepository,
    session_id: str | None = None,
    chat_client: KimiChatClient | None = None,
) -> PreparedChat:
    active_session = session_id
    if active_session is None or not repository.session_exists(active_session):
        active_session = repository.create_session()
    history = repository.list_messages(active_session)
    knowledge_context = KnowledgeContextService().build_context(query)
    teacher_style = ""
    if hasattr(repository, "db"):
        teacher_style = MemoryService().get_preferences(repository.db).teacher_style
    active_chat_client = chat_client or create_chat_client()
    complete_signature = inspect.signature(active_chat_client.complete)
    if "teacher_style" in complete_signature.parameters:
        answer = active_chat_client.complete(
            query=query,
            history=history,
            knowledge_context=knowledge_context,
            teacher_style=teacher_style,
        )
    else:
        answer = active_chat_client.complete(
            query=query,
            history=history,
            knowledge_context=knowledge_context,
        )
    repository.append_message(active_session, role="user", content=query)
    repository.append_message(active_session, role="assistant", content=answer)
    repository.commit()
    return PreparedChat(session_id=active_session, answer=answer)


async def stream_chat(session_id: str, answer: str) -> AsyncGenerator[str, None]:
    yield sse("session", {"session_id": session_id})
    yield sse("text", {"text": answer})
    yield sse("done", {"session_id": session_id})

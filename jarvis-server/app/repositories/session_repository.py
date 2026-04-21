import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self) -> str:
        session_id = uuid.uuid4().hex
        self.db.add(ChatSession(id=session_id))
        return session_id

    def append_message(self, session_id: str, role: str, content: str) -> None:
        self.db.flush()
        sequence = self.db.scalar(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(next_message_sequence=ChatSession.next_message_sequence + 1)
            .returning(ChatSession.next_message_sequence)
        )
        if sequence is None:
            raise ValueError(f"unknown chat session: {session_id}")
        self.db.add(
            ChatMessage(
                session_id=session_id,
                sequence=sequence,
                role=role,
                content=content,
            )
        )

    def list_messages(self, session_id: str) -> list[tuple[str, str]]:
        rows = self.db.execute(
            select(ChatMessage.role, ChatMessage.content)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sequence)
        ).all()
        return [(role, content) for role, content in rows]

    def commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def session_exists(self, session_id: str) -> bool:
        return self.db.get(ChatSession, session_id) is not None

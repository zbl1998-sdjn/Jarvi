from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ChatSession, RealtimeEvent


class RealtimeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def append_voice_event(self, session_id: str, event_type: str, payload: str) -> None:
        self.db.flush()
        sequence = self.db.scalar(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                next_realtime_event_sequence=ChatSession.next_realtime_event_sequence + 1,
            )
            .returning(ChatSession.next_realtime_event_sequence)
        )
        if sequence is None:
            raise ValueError(f"unknown chat session: {session_id}")

        self.db.add(
            RealtimeEvent(
                session_id=session_id,
                sequence=sequence,
                event_type=event_type,
                payload=payload,
            )
        )

    def list_events(self, session_id: str) -> list[RealtimeEvent]:
        return list(
            self.db.scalars(
                select(RealtimeEvent)
                .where(RealtimeEvent.session_id == session_id)
                .order_by(RealtimeEvent.sequence)
            )
        )

    def commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

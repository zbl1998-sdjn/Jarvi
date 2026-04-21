from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.repositories.realtime_repository import RealtimeRepository
from app.repositories.session_repository import SessionRepository


def test_append_voice_events_persists_state_and_transcript() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        sessions = SessionRepository(db)
        session_id = sessions.create_session()
        sessions.commit()

        repository = RealtimeRepository(db)
        repository.append_voice_event(
            session_id,
            event_type="voice_state",
            payload='{"state":"listening"}',
        )
        repository.append_voice_event(
            session_id,
            event_type="transcript",
            payload='{"text":"open lesson"}',
        )
        repository.commit()

    with Session(engine) as verification_db:
        verification = RealtimeRepository(verification_db)
        events = verification.list_events(session_id)

    assert [(event.event_type, event.payload) for event in events] == [
        ("voice_state", '{"state":"listening"}'),
        ("transcript", '{"text":"open lesson"}'),
    ]

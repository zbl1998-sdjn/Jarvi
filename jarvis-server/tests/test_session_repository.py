from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import UniqueConstraint, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import ChatMessage, ChatSession
from app.repositories.session_repository import SessionRepository


def test_repository_creates_session_and_messages() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        repository = SessionRepository(db)
        session_id = repository.create_session()
        repository.append_message(session_id, role="user", content="hello")
        repository.append_message(session_id, role="assistant", content="world")
        repository.commit()

    with Session(engine) as db:
        sessions = db.scalars(select(ChatSession)).all()
        messages = db.scalars(select(ChatMessage).order_by(ChatMessage.sequence)).all()

    assert len(sessions) == 1
    assert sessions[0].id == session_id
    assert [item.content for item in messages] == ["hello", "world"]


def test_repository_commit_rolls_back_on_failure() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.rollbacks = 0

        def commit(self) -> None:
            raise RuntimeError("commit failed")

        def rollback(self) -> None:
            self.rollbacks += 1

    db = FakeSession()
    repository = SessionRepository(db)

    try:
        repository.commit()
    except RuntimeError:
        pass
    else:
        raise AssertionError("commit should raise when the session commit fails")

    assert db.rollbacks == 1


def test_repository_reports_whether_session_exists() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        repository = SessionRepository(db)
        session_id = repository.create_session()
        repository.commit()

    with Session(engine) as db:
        repository = SessionRepository(db)
        assert repository.session_exists(session_id) is True
        assert repository.session_exists("missing-session") is False


def test_chat_message_sequences_are_unique_per_session() -> None:
    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in ChatMessage.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("session_id", "sequence") in unique_constraints


def test_repository_allocates_distinct_message_sequences_under_concurrency(tmp_path) -> None:
    database_path = tmp_path / "repository-concurrency.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with session_factory() as db:
        repository = SessionRepository(db)
        session_id = repository.create_session()
        repository.append_message(session_id, role="user", content="seed")
        repository.commit()

    def append_message(content: str) -> None:
        with session_factory() as db:
            repository = SessionRepository(db)
            repository.append_message(session_id, role="assistant", content=content)
            repository.commit()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(append_message, content) for content in ("first", "second")]
        for future in futures:
            future.result()

    with session_factory() as db:
        messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sequence, ChatMessage.id)
        ).all()

    assert [message.sequence for message in messages] == [1, 2, 3]

from sqlalchemy import inspect

from app.db import Base, get_engine
from app.models import MemoryFact, SessionArtifact, UserProfileFact


def test_cognitive_core_tables_exist():
    engine = get_engine()
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())

    assert "memory_facts" in tables
    assert "user_profile_facts" in tables
    assert "session_artifacts" in tables

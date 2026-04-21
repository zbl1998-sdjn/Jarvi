import pytest

from app import db as db_module


@pytest.fixture(autouse=True)
def isolated_app_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    runtime_config_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr(
        "app.services.runtime_config_service.RUNTIME_CONFIG_PATH",
        runtime_config_path,
    )
    db_module.reset_database()
    db_module.configure_database(f"sqlite+pysqlite:///{database_path.as_posix()}")
    try:
        yield
    finally:
        db_module.reset_database()

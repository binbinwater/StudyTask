import uuid
from datetime import date
from pathlib import Path

import pytest

from studytask import create_app

RUNTIME_DIR = Path(__file__).resolve().parent / "_runtime"


@pytest.fixture
def db_path():
    # The sandbox used for this exercise rejects directories created with
    # mode 0700 (pytest's default tmp_path mode), so tests use an explicitly
    # permissive workspace-local directory instead.
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)
    path = RUNTIME_DIR / f"studytask-{uuid.uuid4().hex}.sqlite3"
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.unlink()


@pytest.fixture
def app(db_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(db_path),
            "SECRET_KEY": "test-only-key",
            "TODAY_OVERRIDE": date(2026, 11, 9),
        }
    )
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_task(client):
    """Create a task through the HTTP form and return its database id."""

    def _create(**overrides):
        data = {
            "name": "链表实验报告",
            "course": "数据结构",
            "description": "完成单链表与双链表实验。",
            "due_date": "2026-11-10",
            "priority": "高",
        }
        data.update(overrides)
        response = client.post("/tasks", data=data)
        assert response.status_code == 303, response.get_data(as_text=True)
        location = response.headers["Location"]
        return int(location.rstrip("/").split("/")[-1])

    return _create
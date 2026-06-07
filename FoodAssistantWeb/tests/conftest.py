import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)

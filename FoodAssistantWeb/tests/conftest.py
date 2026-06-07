import pytest
from fastapi.testclient import TestClient

from app import config, db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    test_db = tmp_path / "test.db"
    test_url = f"sqlite:///{test_db}"
    test_engine = create_engine(test_url, connect_args={"check_same_thread": False})
    
    monkeypatch.setattr(config, "DB_PATH", test_db)
    monkeypatch.setattr(db, "engine", test_engine)
    monkeypatch.setattr(db, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=test_engine))
    db.init_db()
    yield


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


import os

os.environ["DATABASE_URL"] = "sqlite:///./test_kith.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_path = "test_kith.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.database import Base, engine
    from app.models import user  # noqa: F401  registers the table

    Base.metadata.create_all(bind=engine)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)

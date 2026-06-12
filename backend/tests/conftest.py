import os

os.environ["DATABASE_URL"] = "sqlite:///./test_kith.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test"
os.environ["NEO4J_DATABASE"] = "neo4j"
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_path = "test_kith.db"

    from app.database import Base, engine
    from app.models import user  # noqa: F401  registers the table

    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)

    Base.metadata.create_all(bind=engine)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def db_session():
    db_path = "test_kith.db"

    from app.database import Base, SessionLocal, engine
    import app.models  # noqa: F401  registers all tables

    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)

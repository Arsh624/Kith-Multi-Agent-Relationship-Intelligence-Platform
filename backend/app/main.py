from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
import app.models  # noqa: F401  registers all model tables
from app.routers import auth, graph, health, paste, people

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)
app.include_router(graph.router)
app.include_router(people.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

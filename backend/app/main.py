import asyncio
import os
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
import app.models  # noqa: F401  registers all model tables
from app.routers import (
    auth,
    companies,
    graph,
    health,
    intro,
    paste,
    people,
    search,
    tasks,
)

Base.metadata.create_all(bind=engine)


async def _keep_warm(url: str) -> None:
    # Ping ourselves every 10 minutes so the free host never idles into a
    # cold start. Best effort; failures are ignored.
    while True:
        await asyncio.sleep(600)
        try:
            await asyncio.to_thread(
                lambda: urllib.request.urlopen(url, timeout=15).read()
            )
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    base = os.getenv("RENDER_EXTERNAL_URL")
    task = asyncio.create_task(_keep_warm(base.rstrip("/") + "/health")) if base else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(title="Kith API", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)
app.include_router(graph.router)
app.include_router(people.router)
app.include_router(intro.router)
app.include_router(companies.router)
app.include_router(tasks.router)
app.include_router(search.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

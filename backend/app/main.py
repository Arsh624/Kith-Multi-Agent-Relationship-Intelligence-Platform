from fastapi import FastAPI

from app.database import Base, engine
import app.models  # noqa: F401  registers all model tables
from app.routers import auth, health, paste

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)

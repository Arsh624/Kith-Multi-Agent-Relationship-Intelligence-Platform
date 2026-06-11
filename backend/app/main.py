from fastapi import FastAPI

from app.database import Base, engine
from app.models import user  # noqa: F401  registers the User table
from app.routers import auth, health

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)

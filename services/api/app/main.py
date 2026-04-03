from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config.settings import get_settings
from app.db.migrations import apply_migrations


@asynccontextmanager
async def lifespan(_: FastAPI):
    apply_migrations()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)
app.include_router(router)

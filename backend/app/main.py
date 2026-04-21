from __future__ import annotations

from fastapi import FastAPI

from backend.api.routes import router
from backend.app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}

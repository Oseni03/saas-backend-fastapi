from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBDep
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@router.get("/ready")
async def ready(db: DBDep) -> dict:
    """Readiness probe — checks DB connectivity."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}

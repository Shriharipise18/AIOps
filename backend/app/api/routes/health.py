"""
Health-check router.
Exposes GET /api/v1/health with detailed status of all downstream services.
"""
import asyncio
import time
from fastapi import APIRouter
from pydantic import BaseModel
from app.db.database import check_db_connection
from app.services.redis_service import check_redis_connection
from app.services.llm.factory import llm_health
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


class ServiceStatus(BaseModel):
    status: str          # "ok" | "error" | "disabled"
    latency_ms: float
    provider: str | None = None
    model: str | None = None


class HealthResponse(BaseModel):
    status: str          # overall
    version: str
    environment: str
    services: dict[str, ServiceStatus]


async def _timed_check(check_fn) -> ServiceStatus:
    """Run a boolean check function and measure wall-clock latency."""
    t0 = time.monotonic()
    try:
        ok = await check_fn()
    except Exception as exc:
        logger.warning("Health check failed: %s", exc)
        ok = False
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return ServiceStatus(
        status="ok" if ok else "error",
        latency_ms=latency_ms,
    )


@router.get("/health", response_model=HealthResponse, summary="System health check")
async def health_check() -> HealthResponse:
    """
    Returns the health status of the application and its dependencies.
    """
    logger.info("Health check requested")

    if settings.REDIS_ENABLED:
        db_status, redis_status = await asyncio.gather(
            _timed_check(check_db_connection),
            _timed_check(check_redis_connection),
        )
    else:
        db_status = await _timed_check(check_db_connection)
        redis_status = ServiceStatus(status="disabled", latency_ms=0)

    overall = "ok" if db_status.status == "ok" and redis_status.status in {"ok", "disabled"} else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services={
            "database": db_status,
            "redis": redis_status,
            "ai": ServiceStatus(**llm_health(), latency_ms=0),
        },
    )

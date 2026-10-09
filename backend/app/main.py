"""
FastAPI application entry point.
Configures middleware, lifespan events, and mounts the API router.
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.database import close_db, init_db
from app.services.redis_service import check_redis_connection, close_redis

# Initialise logging before anything else
setup_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and graceful shutdown of resources."""
    logger.info("=== %s v%s starting up ===", settings.APP_NAME, settings.APP_VERSION)

    # MongoDB
    try:
        await init_db()
        logger.info("MongoDB connection ready")
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", e)

    # Redis
    if not settings.REDIS_ENABLED:
        logger.info("Redis disabled by configuration (REDIS_ENABLED=false)")
    else:
        try:
            if await check_redis_connection():
                logger.info("Redis connection ready")
            else:
                logger.warning("Redis is enabled but did not respond to a health check")
        except Exception as e:
            logger.warning("Redis is enabled but unavailable: %s", e)

    logger.info("=== Startup complete — environment: %s ===", settings.ENVIRONMENT)
    yield

    # Shutdown
    logger.info("=== Shutting down ===")
    await close_redis()
    await close_db()
    logger.info("=== Shutdown complete ===")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Repository-aware DevOps workflow backed by MongoDB.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every HTTP request with method, path, status and duration."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        "%s %s -> %s  (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Root & API routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
    }


app.include_router(api_router, prefix=settings.API_PREFIX)

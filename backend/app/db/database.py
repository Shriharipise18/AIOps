"""MongoDB connection lifecycle and database dependency."""
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

mongo_client = AsyncMongoClient(
    settings.MONGODB_URL.get_secret_value(),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
)
database = mongo_client[settings.MONGODB_DATABASE]


async def get_db():
    """Provide the configured MongoDB database to API routes."""
    yield database


async def init_db() -> None:
    """Verify MongoDB and create the indexes used by the workflow."""
    await mongo_client.admin.command("ping")
    await database.projects.create_index("created_at")
    await database.projects.create_index([("status", 1), ("source_type", 1), ("created_at", -1)])
    await database.projects.create_index("name")
    await database.artifact_generations.create_index(
        [("project_id", 1), ("artifact_version", -1)], unique=True
    )
    await database.validation_runs.create_index(
        [("project_id", 1), ("created_at", -1)]
    )
    await database.repair_attempts.create_index(
        [("project_id", 1), ("source_generation_id", 1)]
    )
    await database.deployments.create_index([("project_id", 1), ("created_at", -1)])
    logger.info("MongoDB connected; workflow indexes are ready")


async def check_db_connection() -> bool:
    """Ping MongoDB and return its availability for the health endpoint."""
    try:
        await mongo_client.admin.command("ping")
        return True
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)
        return False


async def close_db() -> None:
    """Close the async client during application shutdown."""
    await mongo_client.close()
    logger.info("MongoDB connection closed")

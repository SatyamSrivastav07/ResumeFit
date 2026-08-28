import logging
from typing import Any

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseConfigurationError(RuntimeError):
    """Raised when MongoDB is required but not configured."""


_client: AsyncMongoClient | None = None


def get_database() -> Any:
    global _client
    if not settings.mongodb_uri:
        raise DatabaseConfigurationError("MONGODB_URI is not configured.")
    if _client is None:
        _client = AsyncMongoClient(
            settings.mongodb_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=5_000,
        )
    return _client[settings.mongodb_database]


async def initialize_mongodb() -> None:
    if not settings.mongodb_uri:
        logger.warning("MongoDB is not configured; persistent endpoints will return 503.")
        return
    database = get_database()
    try:
        await database.command("ping")
        await database.users.create_index("firebase_uid", unique=True)
        await database.resumes.create_index("resume_id", unique=True)
        await database.resumes.create_index("user_id")
        await database.resumes.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await database.jobs.create_index("job_id", unique=True)
        await database.jobs.create_index("user_id")
        await database.jobs.create_index("resume_id")
        await database.jobs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await database.optimizations.create_index("optimization_id", unique=True)
        await database.optimizations.create_index("user_id")
        await database.optimizations.create_index("job_id")
        await database.optimizations.create_index("resume_id")
        await database.optimizations.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    except PyMongoError:
        logger.exception("MongoDB initialization failed.")
        raise


async def close_mongodb() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None

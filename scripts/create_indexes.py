"""
Creates MongoDB indexes required for VeritasAI collections.
Run once after provisioning a new Atlas cluster:

    python -m scripts.create_indexes
"""
from __future__ import annotations

import asyncio

from db.user_repository import get_database
from core.logging import logger


async def main() -> None:
    db = await get_database()

    await db["users"].create_index("email", unique=True)
    await db["users"].create_index("user_id", unique=True)

    await db["results"].create_index([("user_id", 1), ("timestamp", -1)])
    await db["results"].create_index("job_id")

    await db["usage"].create_index([("user_id", 1), ("date", -1)], unique=True)

    await db["alerts"].create_index([("user_id", 1)])

    logger.info("indexes_created")


if __name__ == "__main__":
    asyncio.run(main())
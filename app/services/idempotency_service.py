import json
import asyncio
from app.storage.redis_client import redis_client

locks = {}

CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def get_lock(key: str):
    if key not in locks:
        locks[key] = asyncio.Lock()
    return locks[key]


async def wait_for_completion(key: str):
    while True:
        existing = redis_client.get(key)

        if existing:
            data = json.loads(existing)

            if data["status"] == "COMPLETED":
                return data

        await asyncio.sleep(0.1)
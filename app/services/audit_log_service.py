import json
from datetime import datetime, timezone

from fastapi import Request

from app.services.rate_limiter import get_client_ip
from app.storage.redis_client import redis_client

AUDIT_LOG_KEY = "audit_logs"
AUDIT_LOG_TTL_SECONDS = 60 * 60 * 24 * 30
AUDIT_LOG_MAX_ENTRIES = 10000


def build_audit_event(
    request: Request,
    status: str,
    cache_hit: bool,
) -> dict:
    idempotency_key = request.headers.get("Idempotency-Key", "")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "idempotency_key": idempotency_key,
        "client_ip": get_client_ip(request),
        "status": status,
        "cache_hit": cache_hit,
    }


def append_audit_event(event: dict) -> None:
    redis_client.rpush(AUDIT_LOG_KEY, json.dumps(event))
    redis_client.ltrim(AUDIT_LOG_KEY, -AUDIT_LOG_MAX_ENTRIES, -1)
    redis_client.expire(AUDIT_LOG_KEY, AUDIT_LOG_TTL_SECONDS)
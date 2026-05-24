from time import time

from fastapi import Request

from app.storage.redis_client import redis_client

RATE_LIMIT_MAX_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    current_window = int(time() // RATE_LIMIT_WINDOW_SECONDS)
    key = f"rate_limit:{client_ip}:{current_window}"

    request_count = redis_client.incr(key)

    if request_count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS + 1)

    if request_count > RATE_LIMIT_MAX_REQUESTS:
        retry_after = RATE_LIMIT_WINDOW_SECONDS - int(time() % RATE_LIMIT_WINDOW_SECONDS)
        return False, retry_after

    return True, 0
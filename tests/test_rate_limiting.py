from fastapi.testclient import TestClient

import app.routes.payments as payments_route
import app.services.idempotency_service as idempotency_service
import app.services.rate_limiter as rate_limiter
from app.main import app


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def incr(self, key):
        current = int(self.store.get(key, 0))
        current += 1
        self.store[key] = current
        return current

    def expire(self, key, seconds):
        return True


async def _no_sleep(*args, **kwargs):
    return None


def test_rate_limit_blocks_sixth_request(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(payments_route, "redis_client", fake_redis)
    monkeypatch.setattr(idempotency_service, "redis_client", fake_redis)
    monkeypatch.setattr(rate_limiter, "redis_client", fake_redis)
    monkeypatch.setattr(payments_route.asyncio, "sleep", _no_sleep)

    client = TestClient(app)
    headers = {"Idempotency-Key": "rate-limit-test"}
    payload = {"amount": 100, "currency": "USD"}

    for _ in range(5):
        response = client.post("/process-payment", json=payload, headers=headers)
        assert response.status_code == 201

    response = client.post("/process-payment", json=payload, headers=headers)

    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests. Limit is 5 requests per minute per IP."
    assert response.headers["Retry-After"]
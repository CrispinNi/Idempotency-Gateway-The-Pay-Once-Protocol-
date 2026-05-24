import json

from fastapi.testclient import TestClient

import app.routes.payments as payments_route
import app.services.audit_log_service as audit_log_service
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

    def rpush(self, key, value):
        self.store.setdefault(key, []).append(value)

    def ltrim(self, key, start, end):
        values = self.store.get(key, [])
        self.store[key] = values[start:]
        return True


async def _no_sleep(*args, **kwargs):
    return None


def test_audit_log_records_success_and_cache_hit(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(payments_route, "redis_client", fake_redis)
    monkeypatch.setattr(idempotency_service, "redis_client", fake_redis)
    monkeypatch.setattr(rate_limiter, "redis_client", fake_redis)
    monkeypatch.setattr(audit_log_service, "redis_client", fake_redis)
    monkeypatch.setattr(payments_route.asyncio, "sleep", _no_sleep)

    client = TestClient(app)
    headers = {"Idempotency-Key": "audit-log-test"}
    payload = {"amount": 100, "currency": "USD"}

    first_response = client.post("/process-payment", json=payload, headers=headers)
    second_response = client.post("/process-payment", json=payload, headers=headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    audit_entries = [json.loads(entry) for entry in fake_redis.store["audit_logs"]]

    assert len(audit_entries) == 2
    assert audit_entries[0]["idempotency_key"] == "audit-log-test"
    assert audit_entries[0]["client_ip"] == "testclient"
    assert audit_entries[0]["status"] == "SUCCESS"
    assert audit_entries[0]["cache_hit"] is False
    assert audit_entries[1]["status"] == "SUCCESS"
    assert audit_entries[1]["cache_hit"] is True
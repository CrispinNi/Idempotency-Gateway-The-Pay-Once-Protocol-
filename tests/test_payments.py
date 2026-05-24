from fastapi.testclient import TestClient
from app.main import app

# Inject a FakeRedis and patch modules that reference `redis_client`
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
        if end == -1:
            self.store[key] = values[start:]
        else:
            self.store[key] = values[start : end + 1]
        return True


fake_redis = FakeRedis()

import app.routes.payments as payments_route
import app.services.idempotency_service as idempotency_service
import app.services.rate_limiter as rate_limiter
import app.services.audit_log_service as audit_log_service

payments_route.redis_client = fake_redis
idempotency_service.redis_client = fake_redis
rate_limiter.redis_client = fake_redis
audit_log_service.redis_client = fake_redis

client = TestClient(app)


def test_first_payment():

    response = client.post(
        "/process-payment",
        headers={
            "Idempotency-Key": "abc123"
        },
        json={
            "amount": 100,
            "currency": "GHS"
        }
    )

    assert response.status_code == 201
    assert response.json() == {
        "message": "Charged 100 GHS"
    }


def test_duplicate_payment():

    headers = {
        "Idempotency-Key": "duplicate123"
    }

    body = {
        "amount": 100,
        "currency": "GHS"
    }

    client.post(
        "/process-payment",
        headers=headers,
        json=body
    )

    response = client.post(
        "/process-payment",
        headers=headers,
        json=body
    )

    assert response.headers["X-Cache-Hit"] == "true"
    assert response.status_code == 201


def test_different_payload_same_key():

    headers = {
        "Idempotency-Key": "fraud123"
    }

    client.post(
        "/process-payment",
        headers=headers,
        json={
            "amount": 100,
            "currency": "GHS"
        }
    )

    response = client.post(
        "/process-payment",
        headers=headers,
        json={
            "amount": 500,
            "currency": "GHS"
        }
    )

    assert response.status_code == 409
import json
import asyncio

from fastapi import APIRouter, Header, HTTPException, Response

from app.models.payment import PaymentRequest
from app.storage.redis_client import redis_client
from app.utils.hashing import hash_payload
from app.services.idempotency_service import (
    get_lock,
    wait_for_completion,
    CACHE_TTL_SECONDS
)

router = APIRouter()


@router.post("/process-payment", status_code=201)
async def process_payment(
    payment: PaymentRequest,
    response: Response,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):

    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Idempotency-Key"
        )

    payload_dict = payment.dict()
    payload_hash = hash_payload(payload_dict)

    existing = redis_client.get(idempotency_key)

    # KEY EXISTS
    if existing:
        existing_data = json.loads(existing)

        # PAYLOAD MISMATCH
        if existing_data["request_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used for a different request body."
            )

        # IF PROCESSING -> WAIT
        if existing_data["status"] == "PROCESSING":
            completed_data = await wait_for_completion(idempotency_key)

            response.headers["X-Cache-Hit"] = "true"

            return completed_data["response"]

        # RETURN CACHED RESPONSE
        response.headers["X-Cache-Hit"] = "true"

        return existing_data["response"]

    lock = get_lock(idempotency_key)

    async with lock:

        existing = redis_client.get(idempotency_key)

        # DOUBLE CHECK AFTER LOCK
        if existing:
            existing_data = json.loads(existing)

            response.headers["X-Cache-Hit"] = "true"

            return existing_data["response"]

        # SAVE PROCESSING STATE
        processing_record = {
            "status": "PROCESSING",
            "request_hash": payload_hash
        }

        redis_client.set(
            idempotency_key,
            json.dumps(processing_record),
            ex=CACHE_TTL_SECONDS
        )

        # SIMULATE PAYMENT PROCESSING
        await asyncio.sleep(2)

        response_body = {
            "message": f"Charged {payment.amount} {payment.currency}"
        }

        completed_record = {
            "status": "COMPLETED",
            "request_hash": payload_hash,
            "response": response_body,
            "status_code": 201
        }

        redis_client.set(
            idempotency_key,
            json.dumps(completed_record),
            ex=CACHE_TTL_SECONDS
        )

        return response_body
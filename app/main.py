from fastapi import FastAPI
from fastapi import Request
from app.routes.payments import router as payment_router
from app.services.audit_log_service import append_audit_event, build_audit_event

app = FastAPI(
    title="Idempotency Gateway API",
    version="1.0.0"
)

@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        event = build_audit_event(
            request=request,
            status="ERROR",
            cache_hit=False,
        )
        append_audit_event(event)
        raise

    event = build_audit_event(
        request=request,
        status="SUCCESS" if response.status_code < 400 else "FAILED",
        cache_hit=response.headers.get("X-Cache-Hit", "false").lower() == "true",
    )
    append_audit_event(event)

    return response

app.include_router(payment_router)


@app.get("/")
def root():
    return {
        "message": "Idempotency Gateway Running"
    }
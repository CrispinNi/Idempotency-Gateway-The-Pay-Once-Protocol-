from fastapi import FastAPI
from app.routes.payments import router as payment_router

app = FastAPI(
    title="Idempotency Gateway API",
    version="1.0.0"
)

app.include_router(payment_router)


@app.get("/")
def root():
    return {
        "message": "Idempotency Gateway Running"
    }
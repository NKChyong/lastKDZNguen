from fastapi import FastAPI
from .routers import orders, payments

app = FastAPI(title="Order & Payment API")

app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}

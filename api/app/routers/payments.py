from fastapi import APIRouter, HTTPException, status

router = APIRouter()

fake_payments_db = {}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_payment(payment: dict):
    payment_id = len(fake_payments_db) + 1
    fake_payments_db[payment_id] = payment
    return {"payment_id": payment_id, **payment}

@router.get("/{payment_id}")
async def read_payment(payment_id: int):
    payment = fake_payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"payment_id": payment_id, **payment}

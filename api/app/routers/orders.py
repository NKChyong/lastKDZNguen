from typing import List
from fastapi import APIRouter, HTTPException, status

router = APIRouter()

fake_orders_db = {}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(order: dict):
    order_id = len(fake_orders_db) + 1
    fake_orders_db[order_id] = order
    return {"order_id": order_id, **order}

@router.get("/{order_id}")
async def read_order(order_id: int):
    order = fake_orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, **order}

@router.get("/", response_model=List[dict])
async def list_orders():
    return [{"order_id": oid, **o} for oid, o in fake_orders_db.items()]

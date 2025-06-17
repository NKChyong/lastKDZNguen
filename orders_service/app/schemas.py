from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from typing import List

class OrderCreate(BaseModel):
    amount: Decimal
    description: str | None = None

class OrderRead(BaseModel):
    id: UUID
    amount: Decimal
    description: str | None
    status: str
    class Config:
        orm_mode = True

class OrdersList(BaseModel):
    orders: List[OrderRead]

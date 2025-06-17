from pydantic import BaseModel
from decimal import Decimal

class TopUp(BaseModel):
    amount: Decimal

class Balance(BaseModel):
    balance: Decimal

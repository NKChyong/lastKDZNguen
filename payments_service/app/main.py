import os
import json
from uuid import UUID
from typing import List

import aio_pika
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

app = FastAPI(title="Payments Service")

class PaymentMsg(BaseModel):
    payment_id: int
    order_id: int
    user_id: UUID
    amount: float

class PaymentIn(BaseModel):
    order_id: int
    amount: float = Field(gt=0)

class PaymentOut(PaymentIn):
    id: int

class AccountBalance(BaseModel):
    balance: float

class DepositIn(BaseModel):
    amount: float = Field(gt=0)

UserHeader = Header(..., alias="user_id", convert_underscores=False)

_balances: dict[UUID, float] = {}
_payments: dict[UUID, List[PaymentOut]] = {}
_payment_id = 1


async def get_channel():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    return await connection.channel()

async def publish_order_status(order_id: int, user_id: UUID, status_: str):
    channel = await get_channel()
    q = await channel.declare_queue("order_status_queue", durable=True)
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(
                {"order_id": order_id, "user_id": str(user_id), "status": status_}
            ).encode()
        ),
        routing_key=q.name,
    )


@app.post("/account", status_code=status.HTTP_201_CREATED, summary="Создать счёт")
async def create_account(user_id: UUID = UserHeader):
    """
    Создать новый счёт (если ещё не создан) для пользователя.
    """
    if user_id in _balances:
        raise HTTPException(400, "Счёт уже существует")
    _balances[user_id] = 0.0
    _payments[user_id] = []
    return {"detail": "Счёт создан"}


@app.post("/account/deposit", summary="Пополнить счёт")
async def deposit(
    deposit: DepositIn,
    user_id: UUID = UserHeader,
):
    if user_id not in _balances:
        raise HTTPException(404, "Счёт не найден")
    _balances[user_id] += deposit.amount
    return AccountBalance(balance=_balances[user_id])


@app.get("/account", response_model=AccountBalance, summary="Баланс счёта")
async def get_balance(user_id: UUID = UserHeader):
    if user_id not in _balances:
        raise HTTPException(404, "Счёт не найден")
    return AccountBalance(balance=_balances[user_id])


@app.post(
    "/payments",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Оплатить заказ (внутренний вызов)",
)
async def make_payment(payment: PaymentIn, user_id: UUID = UserHeader):
    """
    **Внимание — это внутренний энд-пойнт, вызываемый Orders Service через RabbitMQ.**  
    Из Swagger его можно вызвать вручную для отладки.
    """
    global _payment_id
    if user_id not in _balances:
        raise HTTPException(404, "Счёт не найден")

    if _balances[user_id] < payment.amount:
        await publish_order_status(payment.order_id, user_id, "failed")
        raise HTTPException(400, "Недостаточно средств")

    _balances[user_id] -= payment.amount
    new_payment = PaymentOut(**payment.model_dump(), id=_payment_id)
    _payment_id += 1
    _payments[user_id].append(new_payment)

    await publish_order_status(payment.order_id, user_id, "paid")
    return new_payment


@app.on_event("startup")
async def start_consumer() -> None:
    """
    Слушаем очередь `payment_queue` и обрабатываем платежи.
    """
    channel = await get_channel()
    queue = await channel.declare_queue("payment_queue", durable=True)

    async def handle(msg: aio_pika.IncomingMessage):
        async with msg.process():
            data = json.loads(msg.body)
            try:
                await make_payment(
                    PaymentIn(order_id=data["order_id"], amount=data["amount"]),
                    user_id=UUID(data["user_id"]),
                )
            except HTTPException:
                pass

    await queue.consume(handle, no_ack=False)

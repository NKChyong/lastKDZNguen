import os
import json
from uuid import UUID
from typing import List

import aio_pika
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

app = FastAPI(title="Orders Service")

class OrderIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    total_amount: float

class OrderOut(OrderIn):
    id: int
    status: str

class OrderStatusUpd(BaseModel):
    order_id: int
    user_id: UUID
    status: str

UserHeader = Header(..., alias="user_id", convert_underscores=False)

_orders: dict[UUID, List[OrderOut]] = {}
_order_id = 1

async def get_channel():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    return await connection.channel()

async def send_payment_task(order: OrderOut, user_id: UUID):
    channel = await get_channel()
    q = await channel.declare_queue("payment_queue", durable=True)
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(
                {
                    "order_id": order.id,
                    "user_id": str(user_id),
                    "amount": order.total_amount,
                }
            ).encode()
        ),
        routing_key=q.name,
    )

@app.post(
    "/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ (запуск оплаты асинхронно)",
)
async def create_order(order: OrderIn, user_id: UUID = UserHeader):
    global _order_id
    new_order = OrderOut(**order.model_dump(), id=_order_id, status="pending")
    _order_id += 1
    _orders.setdefault(user_id, []).append(new_order)

    await send_payment_task(new_order, user_id)
    return new_order


@app.get(
    "/orders",
    response_model=List[OrderOut],
    summary="Список заказов текущего пользователя",
)
async def list_orders(user_id: UUID = UserHeader):
    return _orders.get(user_id, [])


@app.get(
    "/orders/{order_id}",
    response_model=OrderOut,
    summary="Статус конкретного заказа",
)
async def get_order(order_id: int, user_id: UUID = UserHeader):
    for order in _orders.get(user_id, []):
        if order.id == order_id:
            return order
    raise HTTPException(404, "Заказ не найден")


@app.on_event("startup")
async def start_consumer() -> None:
    """
    Слушаем `order_status_queue` и обновляем заказы, когда
    Payments Service сообщит об успешной / неуспешной оплате.
    """
    channel = await get_channel()
    queue = await channel.declare_queue("order_status_queue", durable=True)

    async def handle(msg: aio_pika.IncomingMessage):
        async with msg.process():
            data = OrderStatusUpd(**json.loads(msg.body))
            for order in _orders.get(data.user_id, []):
                if order.id == data.order_id:
                    order.status = data.status
                    break

    await queue.consume(handle, no_ack=False)

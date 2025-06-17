import asyncio
import json
import os
import uuid
import aio_pika
from sqlalchemy import select
from .database import AsyncSessionLocal
from .models import OutboxMessage, Order, OrderStatus

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
OUTBOX_INTERVAL = float(os.getenv("OUTBOX_INTERVAL", "1"))
ORDERS_EXCHANGE = "orders"
PAYMENTS_EXCHANGE = "payments"

async def _publish(payload):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(ORDERS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        await exchange.publish(aio_pika.Message(body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="orders.pay")

async def publish_outbox():
    while True:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(OutboxMessage).where(OutboxMessage.processed == False).limit(100))
            messages = result.scalars().all()
            for msg in messages:
                await _publish(msg.payload)
                msg.processed = True
            await session.commit()
        await asyncio.sleep(OUTBOX_INTERVAL)

async def _handle_payment_event(body: bytes):
    data = json.loads(body)
    order_id = uuid.UUID(data["order_id"])
    success = data["type"] == "PaymentSucceeded"
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.FINISHED if success else OrderStatus.CANCELLED
            await session.commit()

async def consume_payments():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(PAYMENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue("", exclusive=True)
    await queue.bind(exchange, routing_key="payments.#")
    async with queue.iterator() as iterator:
        async for message in iterator:
            async with message.process():
                await _handle_payment_event(message.body)

async def run():
    await asyncio.gather(publish_outbox(), consume_payments())

if __name__ == "__main__":
    asyncio.run(run())

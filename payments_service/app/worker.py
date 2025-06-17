import asyncio
import json
import os
import uuid
from decimal import Decimal
import aio_pika
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal
from .models import InboxMessage, OutboxMessage, Account

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
ORDERS_EXCHANGE = "orders"
PAYMENTS_EXCHANGE = "payments"
OUTBOX_INTERVAL = float(os.getenv("OUTBOX_INTERVAL", "1"))

async def _publish(payload):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(PAYMENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        await exchange.publish(aio_pika.Message(body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key="payments.event")

async def _process_inbox_message(inbox: InboxMessage, session: AsyncSession):
    data = inbox.payload
    user_id = uuid.UUID(data["user_id"])
    order_id = uuid.UUID(data["order_id"])
    amount = Decimal(str(data["amount"]))
    account = await session.get(Account, user_id)
    if not account:
        account = Account(user_id=user_id, balance=0)
        session.add(account)
        await session.flush()
    if account.balance >= amount:
        account.balance -= amount
        event = {"type": "PaymentSucceeded", "order_id": str(order_id), "user_id": str(user_id), "amount": float(amount), "balance_after": float(account.balance)}
    else:
        event = {"type": "PaymentFailed", "order_id": str(order_id), "user_id": str(user_id), "amount": float(amount), "reason": "INSUFFICIENT_FUNDS"}
    session.add(OutboxMessage(payload=event))

async def consume_orders():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(ORDERS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue("", exclusive=True)
    await queue.bind(exchange, routing_key="orders.pay")
    async with queue.iterator() as iterator:
        async for message in iterator:
            async with message.process():
                data = json.loads(message.body)
                async with AsyncSessionLocal() as session:
                    inbox = InboxMessage(payload=data)
                    session.add(inbox)
                    await session.flush()
                    await _process_inbox_message(inbox, session)
                    inbox.processed = True
                    await session.commit()

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

async def run():
    await asyncio.gather(consume_orders(), publish_outbox())

if __name__ == "__main__":
    asyncio.run(run())

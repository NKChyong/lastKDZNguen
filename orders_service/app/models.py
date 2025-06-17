import uuid
import enum
from sqlalchemy import Column, String, Numeric, Enum, Boolean, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .database import Base

class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(scale=2), nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.NEW)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OutboxMessage(Base):
    __tablename__ = "order_outbox"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

import uuid
from sqlalchemy import Column, Numeric, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .database import Base

class Account(Base):
    __tablename__ = "accounts"
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    balance = Column(Numeric(scale=2), nullable=False, default=0)

class InboxMessage(Base):
    __tablename__ = "payment_inbox"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OutboxMessage(Base):
    __tablename__ = "payment_outbox"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

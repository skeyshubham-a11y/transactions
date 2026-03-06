from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    # DECIMAL is mandatory for money. Never use Float.
    balance = Column(DECIMAL(18, 2), default=0.00)
    version = Column(Integer, default=1) # For Optimistic Locking

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String, unique=True, index=True) # Idempotency Key
    sender_id = Column(Integer, ForeignKey("wallets.id"))
    receiver_id = Column(Integer, ForeignKey("wallets.id"))
    amount = Column(DECIMAL(18, 2))
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
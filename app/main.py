from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_db, engine
from .models import Base, Wallet, Transaction
from pydantic import BaseModel
from decimal import Decimal

app = FastAPI()


# Init DB
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Schemas
class TransferRequest(BaseModel):
    sender_user_id: str
    receiver_user_id: str
    amount: float
    reference_id: str  # Unique ID for this transaction (UUID)


@app.post("/create_wallet")
async def create_wallet(
    user_id: str, initial_balance: float, db: AsyncSession = Depends(get_db)
):
    wallet = Wallet(user_id=user_id, balance=initial_balance)
    db.add(wallet)
    await db.commit()
    return {"msg": "Wallet created"}


@app.post("/transfer")
async def transfer_money(request: TransferRequest, db: AsyncSession = Depends(get_db)):
    # 1. Input Validation
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    # 2. START TRANSACTION
    async with db.begin():  # This ensures atomic commit/rollback

        # 3. Check for Idempotency (Has this ref_id been processed?)
        existing_tx = await db.execute(
            select(Transaction).where(Transaction.reference_id == request.reference_id)
        )
        if existing_tx.scalar():
            return {"msg": "Transaction already processed", "status": "DUPLICATE"}

        # 4. LOCKING: Select sender and receiver and LOCK rows
        # We order by ID to prevent Deadlocks (always lock lower ID first)

        # Fetch sender
        sender_stmt = (
            select(Wallet)
            .where(Wallet.user_id == request.sender_user_id)
            .with_for_update()
        )
        sender_result = await db.execute(sender_stmt)
        sender = sender_result.scalar()

        # Fetch receiver
        receiver_stmt = (
            select(Wallet)
            .where(Wallet.user_id == request.receiver_user_id)
            .with_for_update()
        )
        receiver_result = await db.execute(receiver_stmt)
        receiver = receiver_result.scalar()

        if not sender or not receiver:
            raise HTTPException(status_code=404, detail="User not found")

        # 5. Business Logic
        if sender.balance < Decimal(request.amount):
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # 6. Update Balances
        sender.balance -= Decimal(request.amount)
        receiver.balance += Decimal(request.amount)

        # 7. Create Ledger Entry
        tx_record = Transaction(
            reference_id=request.reference_id,
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=Decimal(request.amount),
            status="SUCCESS",
        )
        db.add(tx_record)

        # Auto-commits here due to `async with db.begin()`

    return {"msg": "Transfer successful", "new_balance": sender.balance}

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.models.models import Signal, BinancePrice
from fastapi import  Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.schema.model_schema import SignalBase, BinancePriceBase

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/", response_model=List[SignalBase]) 
async def get_all_signals(
    session: AsyncSession = Depends(get_db)
):
    """
    Fetches all signals from the database.
    """
    result = await session.execute(select(Signal))
    price = await session.execute(select(BinancePrice))
    signals = result.scalars().all()
    return signals
from sqlalchemy import delete

@router.delete("/", status_code=204)
async def delete_all_signals(
    session: AsyncSession = Depends(get_db)
):
    """
    Deletes all signals from the database.
    """
    await session.execute(delete(Signal))
    await session.commit()
    return {"detail": "All signals deleted successfully."}

@router.get("/prices", response_model=List[BinancePriceBase]) 
async def get_all_prices(
    session: AsyncSession = Depends(get_db)
):
    """
    Fetches all signals from the database.
    """
    price = await session.execute(select(BinancePrice))
    prices = price.scalars().all()
    return prices
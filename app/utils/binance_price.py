import httpx
import asyncio
from app.tokens import large_cap_altcoins
from sqlalchemy.orm import Session
from app.models.models import BinancePrice
from app.database import AsyncSessionLocal, AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

async def get_current_prices():
    prices = {}
    async with httpx.AsyncClient() as client:
        for token_info in large_cap_altcoins:
            token_symbol = token_info["symbol"]  # e.g., "FIS/USDT"
            binance_symbol = token_symbol.replace("/", "")  # e.g., "FISUSDT"
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                prices[token_symbol] = float(data["price"]) 
                # Use "FIS/USDT" as display key
            except Exception as e:
                print(f"Error fetching price for {token_symbol} ({binance_symbol}): {e}")
                prices[token_symbol] = None
    return prices
  


async def save_prices_to_db_async(prices: dict, session: AsyncSession):
    try:
        for asset, price in prices.items():
            if price is None:
                continue  # Skip failed or invalid price fetch

            # Check if the asset already exists
            result = await session.execute(select(BinancePrice).filter_by(asset=asset))
            existing = result.scalars().first()

            if existing:
                existing.current_price = price
            else:
                new_entry = BinancePrice(asset=asset, current_price=price)
                session.add(new_entry)

        await session.commit()

    except Exception as e:
        print(f"[DB Error] {e}")
        await session.rollback()


async def main():
    prices = await get_current_prices()
    async with AsyncSessionLocal() as session:
        await save_prices_to_db_async(prices, session)

if __name__ == "__main__":
    asyncio.run(main())

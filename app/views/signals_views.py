from worker.celery_config import app
# import datetime
from worker.celery_config import app
import asyncio
from pydantic import BaseModel
import random
from typing import Dict, List, Any
from dotenv import load_dotenv
import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import redis_client
from datetime import datetime, timezone
import httpx
import asyncio
from app.tokens import large_cap_altcoins
from app.database import AsyncSessionLocal
from app.models.models import Signal
from sqlalchemy.dialects.postgresql import insert as pg_insert
import uuid
from sqlalchemy.orm import Session
from app.database import get_db

from app.database import engine, AsyncSession

router = APIRouter(prefix="/signal", tags=["signals"])

API_KEYS = [
    os.getenv('TAAPI_API_KEY_1'),
    os.getenv('TAAP_API_KEY_2')
]

BULK_ENDPOINT = "https://api.taapi.io/bulk"


class TokenRequest(BaseModel):
    symbols: list[str]


def build_payload(api_key: str, symbol: str) -> Dict[str, Any]:
    return {
        "secret": api_key,
        "construct": {
            "exchange": "binance",
            "symbol": symbol,
            "interval": "5m",
            "indicators": [
                {"indicator": "rsi"},
                {"indicator": "macd"},
                {"indicator": "stochrsi"},
                {"indicator": "ema", "optInTimePeriod": 9},
                {"indicator": "ema", "optInTimePeriod": 21}
            ]
        }
    }


MAX_REQUESTS_PER_MINUTE = 60
REQUEST_INTERVAL = 60 / MAX_REQUESTS_PER_MINUTE
MAX_RETRIES = 3


async def send_bulk_request_async(api_key: str, payload: Dict[str, Any]) -> tuple[Dict[str, Any] | None, int]:
    """Send a single async request with given payload using httpx with rate limiting."""
    async with httpx.AsyncClient() as client:
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    wait_time = REQUEST_INTERVAL * \
                        (1 + random.uniform(0.1, 0.3))  # Add jitter
                    await asyncio.sleep(wait_time)

                response = await client.post(
                    BULK_ENDPOINT,
                    json=payload,
                    timeout=30.0,
                    headers={
                        "User-Agent": f"TradingApp/1.0 (Key: {api_key[:5]})"}
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    print(
                        f"Rate limited. Waiting {retry_after} seconds before retry...")
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code != 200:
                    print(
                        f"API request failed with status {response.status_code}: {response.text}")
                    return None, response.status_code

                return response.json(), 200

            except httpx.RequestError as e:
                print(f"HTTPX Request error (attempt {attempt+1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    return None, -1
                await asyncio.sleep(1 + attempt)

            except Exception as e:
                print(
                    f"An unexpected error occurred (attempt {attempt+1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    return None, -1
                await asyncio.sleep(1 + attempt)

    return None, -1


async def get_all_indicators_async(api_key: str, symbol: str) -> tuple[Dict[str, Any] | None, int]:
    """Get all indicators for a symbol using async requests."""
    payload = build_payload(api_key, symbol)
    data, status_code = await send_bulk_request_async(api_key, payload)
    return data, status_code

from sqlalchemy import select

async def get_last_price(session: AsyncSession, symbol: str):
    stmt = select(Signal).where(Signal.symbol == symbol)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()  # This gives you the `Signal` instance or None

    if not row:
        return None
    print(row.last_buy, row.last_exit, row.last_sell, row.last_hold)
    print(bool(row.last_buy))
    print(bool(row.last_exit))
    print(bool(row.last_sell))
    print(bool(row.last_hold))
    # Check based on priority
    if row.last_buy:
        if row.last_buy_price:
            return row.last_buy_price
        return row.price
    elif row.last_sell:
        if row.last_sell_price:
            return row.last_sell_price
        return row.price
    elif row.last_hold:
        if row.last_hold_price:
            return row.last_hold_price
        return row.price
    elif row.last_exit:
        if row.last_exit_price:
            return row.last_exit_price
        return row.price
    else:
        return None

async def interpret_signal_improved(data: Dict[str, Any], symbol: str, current_price, session: AsyncSession) -> Dict[str, Any]:
    """
    Improved trading signal system with multiple signal strength levels
    """
    try:
        if not data or "data" not in data or not data["data"]:
            print("Invalid data structure for interpretation")
            return {"signal": False, "strength": 0, "signal_type": "NO DATA", "analysis": "Invalid data"}

        # Extract indicators
        rsi_data = None
        macd_data = None
        stochrsi_data = None
        ema_values = []

        for entry in data["data"]:
            indicator = entry.get("indicator")
            result = entry.get("result", {})

            if indicator == "rsi":
                rsi_data = result
            elif indicator == "macd":
                macd_data = result
            elif indicator == "stochrsi":
                stochrsi_data = result
            elif indicator == "ema":
                ema_values.append(entry)

        if not all([rsi_data, macd_data, stochrsi_data]) or len(ema_values) < 2:
            print("Missing required indicators for signal interpretation.")
            return {"signal": False, "strength": 0, "signal_type": "INCOMPLETE DATA", "analysis": "Missing indicators"}

        rsi = rsi_data.get("value")
        macd_value = macd_data.get("valueMACD")
        macd_signal = macd_data.get("valueMACDSignal")
        macd_hist = macd_data.get("valueMACDHist")
        stochrsi_k = stochrsi_data.get("valueFastK")
        stochrsi_d = stochrsi_data.get("valueFastD")

        ema9_val = ema_values[0]["result"]["value"] if len(
            ema_values) > 0 and "result" in ema_values[0] and "value" in ema_values[0]["result"] else None
        ema21_val = ema_values[1]["result"]["value"] if len(
            ema_values) > 1 and "result" in ema_values[1] and "value" in ema_values[1]["result"] else None

        if not all(isinstance(val, (int, float)) for val in [rsi, macd_value, macd_signal, macd_hist, stochrsi_k, stochrsi_d, ema9_val, ema21_val]) and \
           any(val is not None for val in [rsi, macd_value, macd_signal, macd_hist, stochrsi_k, stochrsi_d, ema9_val, ema21_val]):
            print("One or more indicator values are not numeric.")
            return {"signal": False, "strength": 0, "signal_type": "INVALID DATA", "analysis": "Non-numeric indicator values"}

        print(f"Technical Indicators for interpretation:")
        print(f"RSI: {rsi:.2f}" if rsi is not None else "RSI: N/A")
        print(
            f"MACD: {macd_value:.2f}, Signal: {macd_signal:.2f}, Hist: {macd_hist:.2f}" if macd_value is not None and macd_signal is not None and macd_hist is not None else "MACD: N/A")
        print(
            f"StochRSI K: {stochrsi_k:.2f}, D: {stochrsi_d:.2f}" if stochrsi_k is not None and stochrsi_d is not None else "StochRSI: N/A")
        print(
            f"EMA9: {ema9_val:.2f}, EMA21: {ema21_val:.2f}" if ema9_val is not None and ema21_val is not None else "EMA: N/A")

        signal_strength = 0
        bullish_factors = []
        bearish_factors = []
        last_sell = None
        last_exit = None
        last_buy = None
        last_hold = None
        last_sell_price = None
        last_exit_price = None
        last_buy_price = None
        last_hold_price = None

        if rsi is not None:
            if 30 <= rsi <= 70:
                signal_strength += 10
                bullish_factors.append(f"RSI neutral ({rsi:.1f})")
            elif rsi < 30:
                signal_strength += 20
                bullish_factors.append(
                    f"RSI oversold ({rsi:.1f}) - bounce potential")
            elif rsi > 70:
                bearish_factors.append(f"RSI overbought ({rsi:.1f})")

        if macd_value is not None and macd_signal is not None:
            if macd_value > macd_signal:
                signal_strength += 15
                bullish_factors.append("MACD bullish crossover")
            else:
                bearish_factors.append("MACD bearish")

        if macd_hist is not None:
            if macd_hist > 0:
                signal_strength += 10
                bullish_factors.append("MACD histogram positive")
            else:
                bearish_factors.append("MACD histogram negative")

        if stochrsi_k is not None and stochrsi_d is not None:
            if stochrsi_k < 20 and stochrsi_d < 20:
                signal_strength += 20
                bullish_factors.append("StochRSI oversold - strong buy signal")
            elif stochrsi_k > stochrsi_d:
                signal_strength += 10
                bullish_factors.append("StochRSI K > D")
            elif stochrsi_k > 80 and stochrsi_d > 80:
                bearish_factors.append("StochRSI overbought")

        # EMA Trend Analysis (0-25 points)
        if ema9_val is not None and ema21_val is not None and ema21_val != 0:
            ema_diff_percent = ((ema9_val - ema21_val) / ema21_val) * 100
            if ema9_val > ema21_val:
                if ema_diff_percent > 0.5:
                    signal_strength += 25
                    bullish_factors.append(
                        f"Strong uptrend (EMA9 {ema_diff_percent:.2f}% above EMA21)")
                else:
                    signal_strength += 15
                    bullish_factors.append("Weak uptrend (EMA9 > EMA21)")
            else:
                if ema_diff_percent < -0.5:
                    bearish_factors.append(
                        f"Strong downtrend (EMA9 {abs(ema_diff_percent):.2f}% below EMA21)")
                else:
                    signal_strength += 5
                    bullish_factors.append(
                        "Trend weakening (EMA9 approaching EMA21)")

        if macd_value is not None and rsi is not None:
            if macd_value > 0 and rsi > 45:
                signal_strength += 10
                bullish_factors.append("Positive momentum confirmed")
        # print(symbol)
        # Signal determination
        if signal_strength >= 70:
            signal_type = "STRONG BUY"
            last_buy = datetime.now(timezone.utc).replace(tzinfo=None)
            last_buy_price = await get_last_price(session, symbol)
            should_buy = True
        elif signal_strength >= 50:
            signal_type = "BUY"
            last_buy = datetime.now(timezone.utc).replace(tzinfo=None)
            last_buy_price = await get_last_price(session, symbol)
            should_buy = True
        elif signal_strength >= 35:
            signal_type = "WEAK BUY"
            last_buy = datetime.now(timezone.utc).replace(tzinfo=None)
            last_buy_price = await get_last_price(session, symbol)
            should_buy = True
        elif signal_strength >= 25:
            signal_type = "HOLD/WATCH"
            last_hold = datetime.now(timezone.utc).replace(tzinfo=None)
            last_hold_price = await get_last_price(session, symbol)
            should_buy = False
        elif signal_strength >= 15:
            signal_type = "WEAK SELL"
            last_sell = datetime.now(timezone.utc).replace(tzinfo=None)
            last_sell_price = await get_last_price(session, symbol)
            should_buy = False
        elif signal_strength >= 5:
            signal_type = "SELL"
            last_sell = datetime.now(timezone.utc).replace(tzinfo=None)
            last_sell_price = await get_last_price(session, symbol)
            should_buy = False
        else:
            signal_type = "STRONG SELL"
            last_sell = datetime.now(timezone.utc).replace(tzinfo=None)
            last_sell_price = await get_last_price(session, symbol)
            should_buy = False

        # [Omitted: print debug info and the return dict generation]

        return {
            "signal": should_buy,
            "strength": signal_strength,
            "signal_type": signal_type,
            "bullish_factors": bullish_factors,
            "bearish_factors": bearish_factors,
            "rsi": rsi,
            "volatility_pct": random.uniform(0.1, 5.0),
            "analysis": {
                "rsi": rsi,
                "macd_bullish": macd_value > macd_signal if macd_value is not None and macd_signal is not None else None,
                "trend_bullish": ema9_val > ema21_val if ema9_val is not None and ema21_val is not None else None,
                "stochrsi_oversold": stochrsi_k < 20 and stochrsi_d < 20 if stochrsi_k is not None and stochrsi_d is not None else None
            },
            "name": symbol,
            "current_price": current_price,
            "rsi_val": round(rsi, 2) if rsi is not None else None,
            "current_signal": "BUY" if should_buy else "SELL" if signal_strength < 25 else "HOLD",
            "last_buy": last_buy,
            "last_buy_price": last_buy_price,
            "last_sell": last_sell,
            "last_sell_price": last_sell_price,
            "last_hold": last_hold,
            "last_hold_price": last_hold_price,
            "last_exit": last_exit,
            "last_exit_price": last_sell_price,
            "price": current_price,
        }

    except Exception as e:
        print(f"Error interpreting data: {e}")
        traceback.print_exc()
        return {"signal": False, "strength": 0, "signal_type": "ERROR", "analysis": f"Error: {str(e)}"}


async def get_last_prices(session: AsyncSession, symbol: str):
    """Get the last prices for each signal type"""
    stmt = select(Signal).where(Signal.symbol == symbol)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if not row:
        return {
            'last_buy_price': None,
            'last_sell_price': None,
            'last_hold_price': None,
            'last_exit_price': None
        }
    
    return {
        'last_buy_price': row.last_buy_price,
        'last_sell_price': row.last_sell_price,
        'last_hold_price': row.last_hold_price,
        'last_exit_price': row.last_exit_price
    }


async def get_current_price(symbol):
    # Convert "FIS/USDT" to "FISUSDT" for Binance API
    binance_symbol = symbol.replace("/", "")
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return float(data["price"])


async def fetch_signals_for_symbol(symbol_data: Dict[str, str], api_keys: List[str]) -> Dict[str, Any] | None:
    """Fetches signals for a single symbol with improved key rotation."""
    symbol = symbol_data["symbol"]
    name = symbol_data["name"]
    
    for i, api_key in enumerate(api_keys):
        # print(f"Fetching {symbol} ({name}) with API Key: {api_key[:5]}...")
        raw_data, status = await get_all_indicators_async(api_key, symbol)

        if status == 200 and raw_data:
            # print(f"Successfully fetched raw data for {symbol} ({name}).")
            current_price = await get_current_price(symbol)
            # print(current_price)
            async for session in get_db():
                interpreted_signal = await interpret_signal_improved(raw_data, symbol, current_price, session)
            # interpreted_signal = interpret_signal_improved(
            #     raw_data, symbol, current_price)
            return {
                "symbol": symbol,
                "name": name,  # Include the name in the result
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # "raw_data": raw_data,
                "current_price": current_price,
                "interpreted_signal": interpreted_signal
                
            }
        elif status == 429:
            # print(f"Rate limit hit for {api_key[:5]}")
            if i < len(api_keys) - 1:
                print("Trying next key...")
                await asyncio.sleep(random.uniform(1, 3))  # Small backoff
            else:
                print("All keys rate limited. Waiting before retry...")
                # Longer wait if all keys are rate limited
                await asyncio.sleep(10)
                # Retry
                return await fetch_signals_for_symbol(symbol_data, api_keys)
        else:
            print(
                f"Failed to fetch {symbol} ({name}) with API Key {api_key[:5]}, status: {status}")

    print(f"Failed to fetch data for {symbol} ({name}) after trying all API keys.")
    return None



async def fetch_all_signals(symbol_list: List[Dict[str, str]], api_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetches signals for a list of symbol dictionaries with rate limiting."""
    successful_results = []
    current_key_index = 0
    total_requests = 0

    # Process symbols in batches
    batch_size = min(5, len(symbol_list))
    for i in range(0, len(symbol_list), batch_size):
        batch = symbol_list[i:i + batch_size]

        # Create tasks for current batch
        tasks = []
        for symbol_data in batch:
            api_key = api_keys[current_key_index]
            # print(api_key)
            tasks.append(fetch_signals_for_symbol(symbol_data, api_keys))
            current_key_index = (current_key_index + 1) % len(api_keys)
            total_requests += 1

            # Respect rate limits
            if total_requests % 10 == 0:  # Adjust based on your API limits
                await asyncio.sleep(REQUEST_INTERVAL)

        # Execute batch
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for res in batch_results:
            if isinstance(res, Exception):
                # print(f"Error during signal fetching: {res}")
                # traceback.print_exc()
                continue
            
            elif res:
                successful_results.append(res)
                
    print("Successfully fetched all signals")
    return successful_results



async def save_signals_to_postgres(signals_data: List[Dict[str, Any]]):
    """
    Saves fetched signal data to PostgreSQL.
    Uses an upsert strategy (ON CONFLICT DO UPDATE) to update existing records
    or insert new ones.
    """
    from sqlalchemy.future import select
    from app.models.models import Signal
    if not signals_data:
        print("No signals data to save to PostgreSQL.")
        return

    try:
        async with AsyncSessionLocal() as session:
            for entry in signals_data:
                symbol = entry.get("symbol")
                if not symbol:
                    # print(f"Warning: Signal entry missing 'symbol' key: {entry}")
                    continue

                interpreted_signal_data = entry.get("interpreted_signal", {})
                db_current_price = entry.get("current_price")

                # Get existing record to compare timestamps
                existing_record = await session.execute(
                    select(Signal).where(Signal.symbol == symbol)
                )
                existing_record = existing_record.scalar_one_or_none()

                # Prepare base update values
                update_values = {
                    "symbol": symbol,
                    "name": interpreted_signal_data.get("name"),
                    "rsi": interpreted_signal_data.get("analysis", {}).get("rsi"),
                    "current_signal": interpreted_signal_data.get("current_signal"),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    "signal_type": interpreted_signal_data.get("signal_type"),
                    "price": db_current_price,
                    "timestamp": datetime.fromisoformat(entry.get("timestamp")).astimezone(timezone.utc).replace(tzinfo=None) if entry.get("timestamp") else datetime.utcnow(),
                    "strength": interpreted_signal_data.get("strength"),
                    "ema9": interpreted_signal_data.get("analysis", {}).get("ema9_val"),
                    "ema21": interpreted_signal_data.get("analysis", {}).get("ema21_val"),
                    "volatility_pct": interpreted_signal_data.get("volatility_pct", 0.0),
                    "last_signal": interpreted_signal_data.get("signal_type"),
                }

                # Check and update signal-specific fields only if they're new
                signal_fields = {
                    "last_buy": interpreted_signal_data.get("last_buy"),
                    "last_sell": interpreted_signal_data.get("last_sell"),
                    "last_hold": interpreted_signal_data.get("last_hold"),
                    "last_exit": interpreted_signal_data.get("last_exit"),
                }

                for field, new_timestamp in signal_fields.items():
                    if new_timestamp is not None:
                        # Only update if this is a new signal (timestamp is different)
                        if not existing_record or getattr(existing_record, field) != new_timestamp:
                            update_values[field] = new_timestamp
                            update_values[f"{field}_price"] = db_current_price
                        elif existing_record:
                            # Keep existing price if timestamp hasn't changed
                            update_values[f"{field}_price"] = getattr(existing_record, f"{field}_price")

                stmt = pg_insert(Signal).values(
                    id=interpreted_signal_data.get("id", str(uuid.uuid4())),
                    **update_values
                )

                on_conflict_stmt = stmt.on_conflict_do_update(
                    index_elements=[Signal.symbol],
                    set_=update_values
                )
                
                await session.execute(on_conflict_stmt)
            
            await session.commit()
            print(f"Successfully saved {len(signals_data)} signals to PostgreSQL.")

    except Exception as e:
        print(f"An error occurred saving signals to PostgreSQL: {e}")
        traceback.print_exc()



async def scheduled_signal_update():
    """Scheduled task with rate limit awareness."""
    print(f"Starting scheduled signal update")

    # Process symbols in smaller batches
    symbols_to_fetch = large_cap_altcoins
    batch_size = 245 # Adjust based on your rate limits
    all_results = []

    for i in range(0, len(symbols_to_fetch), batch_size):
        batch = symbols_to_fetch[i:i + batch_size]
        # print(
        #     f"Processing batch {i//batch_size + 1} of {len(symbols_to_fetch)//batch_size + 1}")

        results = await fetch_all_signals(batch, API_KEYS)
        if results:
            all_results.extend(results)
            await save_signals_to_postgres(results)  # Save each batch
        # Wait between batches to respect rate limits
        if i + batch_size < len(symbols_to_fetch):
            await asyncio.sleep(REQUEST_INTERVAL * batch_size)

    print(f"Finished scheduled signal update")
    return all_results
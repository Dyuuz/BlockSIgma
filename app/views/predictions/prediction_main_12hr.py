from fastapi import FastAPI, Depends
from sqlalchemy.dialects.postgresql import insert
from app.database import get_db
from app.database import AsyncSessionLocal
from app.models.models import Symbol, Prediction, TwelveHoursSummary, TwelveHoursBuySummary
from sqlalchemy.future import select
from sqlalchemy import delete, and_, desc, asc, or_
from sqlalchemy import delete
import asyncio
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from app.views.predictions.LSTM_model import get_all_predictions
from app.views.predictions.Hybrid_Model_12hr import main_model
from postgrest.exceptions import APIError
from fastapi import APIRouter
from datetime import datetime, timedelta
from supabase import create_client
from binance.client import Client
from datetime import datetime, timezone
from app.config import settings
import logging
import os
import re
import httpx
from typing import List
from dotenv import load_dotenv
from app.schema.model_schema import PredictionBase_12hr
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from fastapi.responses import JSONResponse
import gc
from app.utils.mem_logger import log_memory
from app.utils.mail_api import send_email_via_brevo

app = FastAPI()
load_dotenv()

router = APIRouter(prefix="/price", tags=["predictions"])
os_supabase_key = bool(os.getenv("SUPABASE_KEY"))
os_supabase_url = bool(os.getenv("SUPABASE_URL"))
supabase_key = os.getenv(
    "SUPABASE_KEY") if os_supabase_key else settings.SUPABASE_KEY
supabase_url = os.getenv(
    "SUPABASE_URL") if os_supabase_url else settings.SUPABASE_URL
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
use_supabase = os.getenv("USE_SUPABASE")
scheduler = BackgroundScheduler(timezone=timezone.utc)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Client(api_key, api_secret)
if use_supabase:
    supabase = create_client(supabase_url, supabase_key)
TABLE_PREDICTION = "predictions_v3_test"
TABLE_SYMBOL = "symbols_test"
CONFLICT_KEY = "symbol"
EXPECTED_JOB_IDS_12hr = ["job_chunk1", "job_chunk2", "job_chunk3"]
results_lock = asyncio.Lock()

twelve_hour_job_state = False

def get_filtered_assetchunk_status(asset_list):
    """
    Returns the assets with active trading status from a list of asset gotten from Binance API
    """
    client = Client(api_key, api_secret)
    exchange_info = client.get_exchange_info()
    print("Starting to filter assets with active trading status from asset_list")

    active_spot_symbols = [symbol['symbol']
                           for symbol in exchange_info['symbols'] if symbol['status'] == 'TRADING']
    chunk = []
    chunk_disabled = []

    for symbol in asset_list:
        quote = "USDT"
        if symbol+quote in active_spot_symbols:
            chunk.append(symbol)
        else:
            chunk_disabled.append(symbol)

    return chunk, chunk_disabled


async def get_asset_chunks(rows):
    """
    Splits a list of asset symbols into chunks of 100 and labels them as 
    'Asset chunk 1', 'Asset chunk 2', etc.
    Used to optimize task execution by breaking large symbol lists into 
    smaller groups for parallel or scheduled processing which is used in
    run_predictions_for_chunk()
    """
    symbols: list[str] = [row["symbol"] for row in rows]
    asset_chunks = {}
    arrays = [symbols[i:i+100] for i in range(0, len(symbols), 100)]

    for idx, array in enumerate(arrays):
        asset_chunks = {f"Asset chunk {idx+1}": array for idx,
                        array in enumerate(arrays)}

    return asset_chunks


async def delete_disabled_assets(symbols_to_delete):
    """
    Deletes disabled assets from predictions_v2 and symbol table
    This ensures inactive assets are not listed in predictions endpoint
    """
    try:
        async with AsyncSessionLocal() as session:
            prediction_result = await session.execute(
                select(Prediction).where(
                    Prediction.symbol.in_(symbols_to_delete))
            )
            prediction = prediction_result.scalars().all()
            disabled_predictions = [{'symbol': sym} for sym in prediction]

            symbol_result = await session.execute(
                select(Symbol).where(Symbol.symbol.in_(symbols_to_delete))
            )
            symbols: List[str] = symbol_result.scalars().all()
            disabled_symbols = [{'symbol': sym} for sym in symbols]

            if disabled_predictions is not None:
                await session.execute(
                    delete(Prediction).where(
                        Prediction.symbol.in_(symbols_to_delete))
                )
                await session.commit()
                print(
                    f"[✔] Deleted {len(disabled_predictions)} rows from 12hr Prediction table.")

            if symbols is not None:
                await session.execute(
                    delete(Symbol).where(Symbol.symbol.in_(symbols_to_delete))
                )
                await session.commit()
                print(
                    f"[✔] Deleted {len(disabled_symbols)} rows from Symbols table.")

            else:
                print("Nothing to delete")
                return

    except Exception as e:
        print("Delete failed:", e)


async def run_predictions_for_chunk():
    """
    Asynchronously runs price predictions for grouped asset chunks.

    - Fetches asset symbols and divides them into predefined chunks.
    - Runs prediction logic for each chunk using a background thread.
    - Filters out disabled assets and only includes active ones from Binance.
    - Upserts prediction results into the database.
    - Schedules a follow-up run 30 minutes before the next expiry.
    - Finalize and update the most recent 12-hour(buy) prediction summary.
    - Create and store a new 12-hour(buy) prediction summary record.

    Logs progress and errors throughout the process.
    """
    try:
        log_memory("12hr Prediction Current memory usage")

        global twelve_hour_job_state
        twelve_hour_job_state = True

        print("🚀 Starting chunk predictions for 12hr...")
        all_results = {}
        final_results = []

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Symbol.symbol))
            symbols: List[str] = result.scalars().all()

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Prediction.symbol, Prediction.asset_name))
            rows = result.all()
            symbol_to_name = {
                symbol: asset_name for symbol, asset_name in rows}

        rp_symbols = [{'symbol': sym} for sym in symbols]
        if not rp_symbols:
            print("Symbols list is empty.")
            return

        chunks_dict = await get_asset_chunks(rp_symbols)
        chunk1 = chunks_dict.get("Asset chunk 1", [])
        chunk2 = chunks_dict.get("Asset chunk 2", [])
        chunk3 = chunks_dict.get("Asset chunk 3", [])

        print(f"Chunk1: {chunk1[0] if chunk1 else 'empty'}")
        print(f"Chunk2: {chunk2[0] if chunk2 else 'empty'}")
        print(f"Chunk3: {chunk3[0] if chunk3 else 'empty'}")

        chunks = {
            "job_chunk1": ("Asset chunk 1", chunk1),
            "job_chunk2": ("Asset chunk 2", chunk2),
            "job_chunk3": ("Asset chunk 3", chunk3),
        }

        for job_id, (label, assets) in chunks.items():
            try:
                asset_list, disabled = get_filtered_assetchunk_status(assets)
                await delete_disabled_assets(disabled)

                # Offload sync model prediction to background thread
                predicted = await asyncio.to_thread(main_model, label, asset_list, symbol_to_name)

                print(f"[{job_id}] ✅ Done.")

            except Exception as e:
                print(f"[✖] Error in {job_id}: {e}")
                continue

            async with results_lock:
                all_results[job_id] = predicted

                if all(jid in all_results for jid in EXPECTED_JOB_IDS_12hr):
                    for res in all_results.values():
                        final_results.extend(res)

                    quote = "USDT"
                    info = await asyncio.to_thread(client.get_exchange_info)
                    active_symbols = {s["symbol"] for s in info["symbols"]}

                    filtered_result = [
                        res for res in final_results
                        if res["symbol"] + quote in active_symbols
                    ]

                    if not filtered_result:
                        print("[✖] No predictions to insert.")
                        return

                    async for db in get_db():
                        se_12hr = await save_exit_12hr_summary(db)
                        se_12hr_buy = await save_exit_12hr_buy_summary(db)

                    if se_12hr is None or se_12hr_buy is None:
                        print("12hr Summary table is still empty!")
                    else:
                        print(
                            "[✔] Successfully saved twelve hours(+buy) summary table")

                    try:
                        stmt = insert(Prediction).values(filtered_result)
                        update_cols = {
                            col.name: getattr(stmt.excluded, col.name)
                            for col in Prediction.__table__.columns
                            if col.name not in ("id", "created_at", "symbol")
                        }

                        stmt = stmt.on_conflict_do_update(
                            index_elements=["symbol"],
                            set_=update_cols,
                        )

                        async with AsyncSessionLocal() as session:
                            await session.execute(stmt)
                            await session.commit()

                        print(f"[✔] Upserted {len(filtered_result)} rows.")

                    except Exception as e:
                        print(f"[✖] PSQL insert failed: {e}")

                    print("[✔] All chunks finished. Saved to 12hr Prediction DB...")
                    all_results.clear()

                else:
                    print(
                        f"Skipping with result lock - waiting on other chunks. [{job_id}]")

        async for db in get_db():
            twelve_hrs_summary = await fetch_12hrs_summary(db)
            await create_12hr_summary(db, twelve_hrs_summary)

        print("[✔] Successfully created twelve hours summary table")

        async for db in get_db():
            twelve_hrs_buy_summary = await fetch_12hrs_buy_summary(db)
            await create_12hr_buy_summary(db, twelve_hrs_buy_summary)

        print("[✔] Successfully created twelve hours buy summary table")

        # Schedule follow-up 30 mins before expiry
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=12)
        rerun_time = expiry - timedelta(minutes=30)
        sg_tz = timezone.utc

        if rerun_time > datetime.now(sg_tz):
            scheduler.add_job(
                run_predictions_for_chunk,
                'date',
                run_date=rerun_time,
                id="job_chunk_12hr",
                replace_existing=True
            )
            print(f"Follow-up task scheduled at {rerun_time}")

        twelve_hour_job_state = False
        log_memory("After 12hr prediction memory usage")
        await send_email_via_brevo("priya@dsl.sg","Bangladesh", "12hr", "Priya")
        await send_email_via_brevo("sam@dsl.sg","Singapore", "12hr", "Sam")
        await send_email_via_brevo("lekanoyesunle@gmail.com","Nigeria", "12hr","Lekan")

        return True

    except Exception as e:
        print(f"[✖] Error in run_predictions_for_chunk: {e}")

    finally:
        # gc.collect()
        logger.info("Session cleared.")
        log_memory("After 12hr prediction memory usage cleared.")

async def save_exit_12hr_summary(session: AsyncSession, update_label="Closure"):
    """
    Update the most recent 12-hour summary with final prediction results.

    This function:
    - Fetches the most recent entry from the TwelveHoursSummary table
    - Retrieves the latest buy prediction details
    - Updates the number of predictions and accuracy from the current summary
    - Optionally appends the instance details based on the `update_label`

    """
    try:
        print(f"Starting to save the last 12hr summary...")
        twelve_hrs_summary = await fetch_12hrs_summary(session)
        from_time = twelve_hrs_summary["from"]
        from_time_check = await session.execute(
            select(TwelveHoursSummary).where(
                TwelveHoursSummary.from_ == from_time)
        )
        current_summary = from_time_check.scalars().all()

        if not current_summary:
            await create_12hr_summary(session, twelve_hrs_summary)
            print("[✔] Successfully created a real-time twelve hours summary table")
            return

        result = await session.execute(
            select(TwelveHoursSummary).order_by(
                desc(TwelveHoursSummary.created_at)).limit(1)
        )
        last_instance = result.scalar_one_or_none()
        last_instance.number_of_predictions = twelve_hrs_summary["number of predictions"]
        last_instance.accuracy = twelve_hrs_summary["accuracy"]
        last_instance.details = await fetch_latest_prediction() if update_label == "Closure" else []

        await session.commit()
        await session.refresh(last_instance)
        return

    except Exception as e:
        print(f"[✖] Failed to save 12hr summary: {e}")


async def save_exit_12hr_buy_summary(session: AsyncSession, update_label="Closure"):
    """
    Update the most recent 12-hour buy summary with final prediction results.

    This function:
    - Fetches the most recent entry from the TwelveHoursBuySummary table
    - Retrieves the latest buy prediction details
    - Updates the number of predictions and accuracy from the current summary
    - Optionally appends the instance details based on the `update_label`

    """
    try:
        print(f"Starting to save the last 12hr buy summary...")
        twelve_hrs_buy_summary = await fetch_12hrs_buy_summary(session)
        from_time = twelve_hrs_buy_summary["from"]
        from_time_check = await session.execute(
            select(TwelveHoursBuySummary).where(
                TwelveHoursBuySummary.from_ == from_time)
        )
        current_summary = from_time_check.scalars().all()

        latest_predictions = await fetch_latest_prediction()
        details = [
            item for item in latest_predictions if item["prediction_status"] == "Buy"]

        if not current_summary:
            await create_12hr_buy_summary(session, twelve_hrs_buy_summary)
            print("[✔] Successfully created a real-time twelve hours buy summary table")
            return

        result = await session.execute(
            select(TwelveHoursBuySummary).order_by(
                desc(TwelveHoursBuySummary.created_at)).limit(1)
        )
        last_instance = result.scalar_one_or_none()
        last_instance.number_of_predictions = twelve_hrs_buy_summary["number of predictions"]
        last_instance.accuracy = twelve_hrs_buy_summary["accuracy"]
        last_instance.details = details if update_label == "Closure" else []

        await session.commit()
        await session.refresh(last_instance)
        return

    except Exception as e:
        print(f"[✖] Failed to save 12hr buy summary: {e}")


async def create_12hr_summary(session: AsyncSession, twelve_hrs_summary):
    """
    Create and save a 12-hour buy summary to the database.

    This function accepts a dictionary containing summary statistics
    for 12-hour "Buy" predictions, and saves the data into the 
    TwelveHoursSummary table. It includes:
    - from, to, number of predictions & accuracy

    The data is committed asynchronously using the provided DB session.
    """
    try:
        print(f"Starting to create 12hr summary...")
        from_time = twelve_hrs_summary["from"]
        to_time = twelve_hrs_summary["to"]
        num_predictions = twelve_hrs_summary["number of predictions"]
        accuracy = twelve_hrs_summary["accuracy"]

        summary = TwelveHoursSummary(
            from_=from_time,
            to=to_time,
            number_of_predictions=num_predictions,
            accuracy=accuracy
        )
        session.add(summary)
        await session.commit()
        await session.refresh(summary)
        return

    except Exception as e:
        print(f"[✖] Failed to create 12hr summary: {e}")


async def create_12hr_buy_summary(session: AsyncSession, twelve_hrs_buy_summary):
    """
    Create and save a 12-hour buy summary to the database.

    This function accepts a dictionary containing summary statistics
    for 12-hour "Buy" predictions, and saves the data into the 
    TwelveHoursBuySummary table. It includes:
    - from, to, number of predictions & accuracy

    The data is committed asynchronously using the provided DB session.
    """

    try:
        print(f"Starting to create 12hr buy summary...")
        from_time = twelve_hrs_buy_summary["from"]
        to_time = twelve_hrs_buy_summary["to"]
        num_predictions = twelve_hrs_buy_summary["number of predictions"]
        accuracy = twelve_hrs_buy_summary["accuracy"]

        summary = TwelveHoursBuySummary(
            from_=from_time,
            to=to_time,
            number_of_predictions=num_predictions,
            accuracy=accuracy
        )
        session.add(summary)
        await session.commit()
        await session.refresh(summary)
        return

    except Exception as e:
        print(f"[✖] Failed to create 12hr buy summary: {e}")


async def get_current_predictions() -> List[str]:
    """
    Fetches all current asset symbols, gets their latest prices from Binance,
    filters out disabled assets, and updates the prediction records accordingly.

    - Determines whether each prediction has been "Reached" based on current vs. predicted price.
    - Updates fields like `achievement`, `time_reached`, `price_difference`, and status flags.
    - Performs a bulk upsert of the predictions into the database.
    - Successive Update of 12hr Summary(accuracy) tables

    Logs progress and errors to the console.
    """
    global twelve_hour_job_state
    if twelve_hour_job_state:
        print("[✖]12hour prediction is currently running!")
        return
    
    print(f"Starting to update 12hr latest prices...")
    all_prices = {}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Symbol.symbol))
        symbols: List[str] = result.scalars().all()

    if not symbols:
        print("Symbols list is empty")
        return

    all_assets, asset_list_disabled = get_filtered_assetchunk_status(symbols)
    await delete_disabled_assets(asset_list_disabled)

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.binance.com/api/v3/ticker/24hr")
        resp.raise_for_status()
        tickers = resp.json()

    quote = "USDT"
    price_map = {item['symbol']: item['lastPrice'] for item in tickers}

    try:
        for symbol in all_assets:
            last_price_str = price_map.get(symbol + quote)
            if last_price_str:
                all_prices[symbol] = float(last_price_str)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Prediction))
            all_rows = result.scalars().all()

        if not all_rows:
            print("Prediction Table is empty.")
            return

        predictions = []
        for row in all_rows:
            item = row.as_dict()
            symbol = item["symbol"]
            previous_current_price = float(item["current_price"])
            predicted = float(item["predicted_price"])
            price_at_predicted_time = float(item["price_at_predicted_time"])
            adjustment_factor = float(0.6)
            prev_dynamic_sl = item["dynamic_sl"]
            prediction_status = item["prediction_status"]

            prediction_status_determiner = True if predicted > price_at_predicted_time else False

            achievement = item["achievement"]
            current = all_prices.get(symbol)
            time_reached = datetime.now(timezone.utc)

            if current is not None:    
                if achievement == "Not Reached" or achievement is None:
                    if prediction_status_determiner == True and current > predicted:
                        item["achievement"] = "Reached"
                        item["time_reached"] = time_reached

                        if prediction_status == "Buy":
                            item["prediction_status"] = "Buy - Reached"
                    
                    elif prediction_status_determiner == False and current < predicted:
                        item["achievement"] = "Reached"
                        item["time_reached"] = time_reached

                        if prediction_status == "Buy":
                            item["prediction_status"] = "Buy - Reached"
                    
                    else:
                        item["achievement"] = "Not Reached"
                
                achievement = item["achievement"]
                prediction_status = item["prediction_status"]

                if achievement == "Reached" and prediction_status in ("Buy", "Reached"):
                    item["prediction_status"] = "Buy - Reached" 

                diff = ((current - price_at_predicted_time) /
                        price_at_predicted_time) * 100
                status = current > previous_current_price
                stat = ((current - predicted) / predicted) * 100

                dynamic_tp = float(item["dynamic_tp"])
                dynamic_sl =((predicted - current) / current) * adjustment_factor * 100
                rrr = dynamic_tp / dynamic_sl if dynamic_sl != 0 else 0
                sl_status = dynamic_sl > prev_dynamic_sl if prev_dynamic_sl else None

                item["current_price"] = round(current, 8)
                item["price_change_status"] = status
                item["price_difference_currently"] = round(diff, 3)
                item["current_status"] = stat >= 1.2
                item["dynamic_sl"] = round(dynamic_sl, 3)
                item["rrr"] = round(rrr, 2)
                item["sl_status"] = sl_status
                predictions.append(item)

        stmt = insert(Prediction).values(predictions)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in Prediction.__table__.columns
            if col.name not in ("id", "created_at", "symbol")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"], set_=update_cols)

        async with AsyncSessionLocal() as session:
            await session.execute(stmt)
            await session.commit()

        print(
            f"[✔] Successfully Upserted {len(predictions)} rows on 12hrs Prediction Table.")

        async for db in get_db():
            await save_exit_12hr_summary(db, update_label="Patch")
            await save_exit_12hr_buy_summary(db, update_label="Patch")

        print(f"[✔] 12hr(buy) summary table updated.")
        log_memory("12hr Current memory usage on refresh")

    except Exception as e:
        print(f"Error during price update: {e}")


async def convert_datetime(iso_input):
    """
    Accepts either:
      - an ISO-style string (e.g. "2025-07-12 09:08:47.435922+00:00")
      - a datetime.datetime (naïve or tz-aware)
    Returns a formatted UTC timestamp like "July 12 25, 09:08 AM UTC+00".
    """
    if isinstance(iso_input, datetime):
        dt = iso_input

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        else:
            dt = dt.astimezone(pytz.UTC)
    else:
        ts = iso_input.replace(" ", "T")
        ts = re.sub(r"([+\-]\d{2})(?!:)", r"\1:00", ts)
        ts = re.sub(
            r"\.(\d+)(?=[+\-])",
            lambda m: "." + m.group(1)[:6].ljust(6, "0"),
            ts
        )
        dt = datetime.fromisoformat(ts)
        dt = dt.astimezone(pytz.UTC)

    base = dt.strftime("%B %d %y, %I:%M %p")
    return f"{base} UTC+00"


@router.get("/latest-predictions")
async def fetch_latest_prediction():
    """
    Asynchronously fetches all predictions from the database, formats the results,
    and returns a list of prediction dictionaries with readable datetime fields.
    1. Sorts the predictions by symbol.
    2. Converts `predicted_time`, `expiry_time`, and `time_reached` to readable formats like "July 12 25, 09:08 AM UTC+00".
    3. Sets `time_reached` to "Not Reached" if it is None.
    4. Moves `price_change_status` to the end of each dictionary for consistency.
    Raises:
        HTTPException: If no predictions are found in the database.
    Returns:
        List[dict]: A list of formatted prediction data dictionaries.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Prediction))
        all_rows = result.scalars().all()

    if not all_rows:
        raise HTTPException(
            status_code=404, detail="12hr Prediction table is empty.")

    formatted = []
    for row in sorted(all_rows, key=lambda x: x.symbol):
        model = PredictionBase_12hr.model_validate(row)
        data = model.model_dump()

        if 'price_change_status' in data:
            pcs = data.pop("price_change_status")
            data["price_change_status"] = pcs

        formatted.append(data)

    predictions = []
    for item in formatted:
        time_reached = item["time_reached"]
        item["predicted_time"] = await convert_datetime(item["predicted_time"])
        item["expiry_time"] = await convert_datetime(item["expiry_time"])
        item["time_reached"] = await convert_datetime(time_reached) if time_reached else "Not Reached"
        predictions.append(item)

    return predictions


async def fetch_12hrs_summary(db: AsyncSession):
    """
    Fetch 12-hour prediction summary.

    This function retrieves summary statistics for all "Buy" predictions 
    in the predictions_v3 prediction table. It calculates and returns:
    - from: The earliest prediction time
    - to: The latest expiry time
    - number of predictions: Total number of predictions
    - accuracy: Percentage of predictions that are marked as "Reached"

    Data is pulled and calculated directly from the database using async queries.
    """

    first_stmt = (select(Prediction).order_by(
        Prediction.predicted_time.asc()).limit(1))
    first_result = await db.execute(first_stmt)
    first = first_result.scalars().first().predicted_time
    # first = await convert_datetime(first)

    dt = datetime.fromisoformat(f"{first}")
    to = dt + timedelta(hours=12)
    # last = await convert_datetime(last)

    count_stmt = select(func.count(Prediction.id))
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar()

    acc_stmt = select(Prediction).where(Prediction.achievement == "Reached")
    acc_result = await db.execute(acc_stmt)
    accuracy_len = len(acc_result.scalars().all())
    accuracy = round((accuracy_len/total_count) *
                     100, 1) if total_count else 0.0
    accuracy_percent = f"{accuracy}%"

    return {
        "from": first,
        "to": to,
        "number of predictions": total_count,
        "accuracy": accuracy_percent
    }


async def fetch_12hrs_buy_summary(db: AsyncSession):
    """
    Fetch 12-hour buy prediction summary.

    This function retrieves summary statistics for all "Buy" predictions 
    in the predictions_v3 prediction table. It calculates and returns:
    - from: The earliest prediction time
    - to: The latest expiry time
    - number of predictions: Total number of "Buy" predictions
    - accuracy: Percentage of "Buy" predictions that are marked as "Reached"

    Data is pulled and calculated directly from the database using async queries.
    """

    first_stmt = (select(Prediction).order_by(
        Prediction.predicted_time.asc()).limit(1))
    first_result = await db.execute(first_stmt)
    first = first_result.scalars().first().predicted_time
    # first = await convert_datetime(first)

    dt = datetime.fromisoformat(f"{first}")
    to = dt + timedelta(hours=12)
    # last = await convert_datetime(last)

    count_stmt = select(Prediction).where(
        or_(
            Prediction.prediction_status == "Buy",
            Prediction.prediction_status == "Buy - Reached"
        )
    )
    count_result = await db.execute(count_stmt)
    total_count = len(count_result.scalars().all())

    acc_stmt = select(Prediction).where(and_(
        Prediction.achievement == "Reached",
        Prediction.prediction_status == "Buy - Reached"
    )
    )
    acc_result = await db.execute(acc_stmt)
    accuracy_len = len(acc_result.scalars().all())
    accuracy = round((accuracy_len/total_count) *
                     100, 1) if total_count else 0.0
    accuracy_percent = f"{accuracy}%"
    return {
        "from": first,
        "to": to,
        "number of predictions": total_count,
        "accuracy": accuracy_percent
    }


@router.get("/twelve-hours-summary")
async def get_12hrs_summary(db: AsyncSession = Depends(get_db)):
    """
    Retrieve 12-hours summary data.

    This endpoint fetches summarized prediction data for every 12-hour interval.
    It returns the following fields for each record:
    - from: Start time of the prediction
    - to: End time of the prediction
    - number_of_predictions: Total predictions made in that interval
    - accuracy: Accuracy of the predictions in percentage

    Results are ordered by the 'to' timestamp in descending order.
    """
    stmt = select(
        TwelveHoursSummary.from_,
        TwelveHoursSummary.to,
        TwelveHoursSummary.number_of_predictions,
        TwelveHoursSummary.accuracy
    ).order_by(desc(TwelveHoursSummary.to))

    result = await db.execute(stmt)
    rows_result = result.fetchall()

    formatted_rows = []
    for row in rows_result:
        row = row._mapping
        formatted_rows.append({
            "from": await convert_datetime(row["from_"]),
            "to": await convert_datetime(row["to"]),
            "number_of_predictions": row["number_of_predictions"],
            "accuracy": row["accuracy"]
        })

    return JSONResponse(content=formatted_rows)


@router.get("/twelve-hours-buy-summary")
async def get_12hrs_buy_summary(db: AsyncSession = Depends(get_db)):
    """
    Retrieve 12-hours-buy summary data.

    This endpoint fetches summarized prediction data for every 12-hour interval.
    It returns the following fields for each record:
    - from: Start time of the prediction
    - to: End time of the prediction
    - number_of_predictions: Total buy predictions made in that interval
    - accuracy: Accuracy of the predictions in percentage

    Results are ordered by the 'to' timestamp in descending order.
    """
    stmt = select(
        TwelveHoursBuySummary.from_,
        TwelveHoursBuySummary.to,
        TwelveHoursBuySummary.number_of_predictions,
        TwelveHoursBuySummary.accuracy
    ).order_by(desc(TwelveHoursBuySummary.to))

    result = await db.execute(stmt)
    rows_result = result.fetchall()

    formatted_rows = []
    for row in rows_result:
        row = row._mapping
        formatted_rows.append({
            "from": await convert_datetime(row["from_"]),
            "to": await convert_datetime(row["to"]),
            "number_of_predictions": row["number_of_predictions"],
            "accuracy": row["accuracy"]
        })

    return JSONResponse(content=formatted_rows)

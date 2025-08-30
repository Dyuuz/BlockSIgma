# worker.trainer.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from worker.celery_config import app
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from binance.client import Client
from supabase import create_client
from celery import group
from celery.result import GroupResult

# === App imports ===
from app.views.predictions.LSTM_model import get_all_predictions
# from app.views.predictions.Hybrid_Model_12hr import main_model_async
from app.views.predictions.prediction_main_12hr import (
    get_filtered_assetchunk_status,
    get_asset_chunks,
    delete_disabled_assets,
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# === Load .env ===
load_dotenv()

# === Global Config ===
TABLE = "predictions_v2"
CONFLICT_KEY = "symbol"
EXPECTED_JOB_IDS = ["job_chunk1", "job_chunk2", "job_chunk3"]
results_lock = threading.Lock()
all_results = {}
final_results = []

# === Load Credentials ===
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

if not (supabase_url and supabase_key and api_key and api_secret):
    raise ValueError("Missing one or more required environment variables")

# === Create Clients Once ===
# supabase = create_client(supabase_url, supabase_key)
# client = Client(api_key, api_secret)


# @app.task(name="worker.trainer.run_predictions_for_chunk")
# def run_predictions_for_chunk(job_id, chunk_label, assets):
#     try:
#         print(f"[{job_id}] Running scheduler...")

#         now = datetime.now(pytz.timezone("Asia/Singapore"))

#         asset_list, disabled = get_filtered_assetchunk_status(assets)
#         delete_disabled_assets(disabled)

#         predicted = main_model_async(chunk_label, asset_list)
#         expiry = now + timedelta(hours=12)

#         for item in predicted:
#             item["predicted_time"] = now.isoformat()
#             item["expiry_time"] = expiry.isoformat()

#         rerun = expiry - timedelta(minutes=30)
#         print(f"[{job_id}] Rerun scheduled at: {rerun}")

#         print(f"[{job_id}] ✅ Done.")
#         return predicted

#     except Exception as e:
#         print(f"[✖] Error in {job_id}: {e}")
#         return []
    

# @app.task(name="worker.trainer.run_all_chunks")
# def run_all_chunks():
#     print("🚀 Starting chunk predictions...")
#     # === Fetch asset chunks ===
#     symbols = supabase.table("symbols").select("symbol").execute().data
#     chunks_dict = get_asset_chunks(symbols)

#     chunk1 = chunks_dict.get("Asset chunk 1", [])
#     chunk2 = chunks_dict.get("Asset chunk 2", [])
#     chunk3 = chunks_dict.get("Asset chunk 3", [])

#     print(f"Chunk1: {chunk1[0] if chunk1 else 'empty'}")
#     print(f"Chunk2: {chunk2[0] if chunk2 else 'empty'}")
#     print(f"Chunk3: {chunk3[0] if chunk3 else 'empty'}")

#     chunks = {
#         "job_chunk1": ("Asset chunk 1", chunk1),
#         "job_chunk2": ("Asset chunk 2", chunk2),
#         "job_chunk3": ("Asset chunk 3", chunk3),
#     }

#     # Send jobs to Celery
#     chunk_jobs = [
#         run_predictions_for_chunk.s(job_id, chunk_name, asset_list)
#         for job_id, (chunk_name, asset_list) in chunks.items()
#     ]
#     group_result: GroupResult = group(chunk_jobs).apply_async()
#     final_results = []

#     # Collect results
#     for result in group_result.get():
#         final_results.extend(result)

#     active_symbols = {sym["symbol"] for sym in client.get_exchange_info()["symbols"]}
#     filtered = [res for res in final_results if res["symbol"] in active_symbols]


#     # Save to Supabase
#     if filtered:
#         supabase.table(TABLE).upsert(filtered, on_conflict="symbol").execute()
#         print(f"✅ Saved {len(filtered)} predictions.")
#     else:
#         print("⚠️ No results to save.")

# if __name__ == "__main__":
#     run_all_chunks.s()
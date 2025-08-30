from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.views.predictions.prediction_main_12hr import get_current_predictions, run_predictions_for_chunk
from app.views.predictions.prediction_main_4hr import get_current_predictions as refresh_4hr_prediction
from app.views.predictions.prediction_main_4hr import run_predictions_for_chunk as run_4hr_prediction
from apscheduler.executors.pool import ThreadPoolExecutor
from app.utils.binance_price import main
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.future import select

from app.routers.user import router as user_router
from app.views.predictions.prediction_main_12hr import router as price_router_12hr
from app.views.predictions.prediction_main_4hr import router as price_router_4hr
from app.routers.signals_router import router as signal_router
from app.views.signals_views import scheduled_signal_update
from app.utils.mail_api import mail_router
# from app.routers.predictions import router as predictions_router
from datetime import timezone
from app.database import engine, Base, init_db

# Create FastAPI app
app = FastAPI(
    title="FastAPI MVC Application",
    description="A simple FastAPI application using MVC pattern",
    version="1.0.0"
)

executors = {
    "asyncio": AsyncIOExecutor(),
    "threadpool": ThreadPoolExecutor(4),
}

job_defaults = {
    'max_instances': 1,
    'coalesce': True,
    'executor':"asyncio",
    'misfire_grace_time': 60
}

scheduler = AsyncIOScheduler(
    executors=executors,
    job_defaults=job_defaults,
    timezone=timezone.utc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(price_router_12hr)
app.include_router(price_router_4hr)
# app.include_router(user_router)
# app.include_router(mail_router)
# app.include_router(signal_router)
# app.include_router(predictions_router)

# Create tables on startup (for dev/demo; use Alembic in prod)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Welcome to MYTRADEGENIUS MVC Application",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    # Runs 5 workers
    print("Starting scheduler...")
    print("Initializing database...")
    await init_db()

    print("Database initialization complete.")
    scheduler.add_job(run_predictions_for_chunk, 'cron', hour='0,12', minute=0, id="job_chunk_12hr", replace_existing=True)
    scheduler.add_job(get_current_predictions, 'interval', seconds=30, replace_existing=True)
    scheduler.add_job(run_4hr_prediction, 'cron', hour='1,2,9,14,17,21', minute=42, id="job_chunk_4hr", replace_existing=True)
    scheduler.add_job(refresh_4hr_prediction, 'interval', seconds=30, replace_existing=True)
    # scheduler.add_job(scheduled_signal_update,'interval', seconds=10, id='signal_update_job', replace_existing=True)
    # scheduler.add_job(main, 'interval', seconds=20, id='binance_price', replace_existing=True)
    print("Scheduled jobs:", scheduler.get_jobs(), flush=True)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
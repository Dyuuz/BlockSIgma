from sqlalchemy.dialects.postgresql import insert
from app.database import get_db
from app.database import AsyncSessionLocal
from app.models.models import Symbol, Prediction
from sqlalchemy.future import select
from sqlalchemy import delete

async def async_fecth_latest_prediction():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Prediction))
        all_rows = result.scalars().all()

        return all_rows
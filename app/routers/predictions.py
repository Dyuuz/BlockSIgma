from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.models import Prediction
from app.schema.model_schema import PredictionCreate, PredictionRead, SymbolRead

# router = APIRouter(prefix="/predictions", tags=["predictions"])

# @router.post("/", response_model=PredictionRead, status_code=status.HTTP_201_CREATED)
# async def create_prediction(payload: PredictionCreate, db: AsyncSession = Depends(get_db)):
#     pred = Prediction(**payload.dict())
#     db.add(pred)
#     await db.commit()
#     await db.refresh(pred)
#     return pred

# @router.get("/", response_model=PredictionRead)
# async def read_prediction(pred_id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Prediction))
#     pred = result.scalars().first()
#     if not pred:
#         raise HTTPException(status_code=404, detail="Not found")
#     return pred

from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.views.predictions.prediction_main_12hr import fetch_latest_prediction as twelvehrpredictions
from app.views.predictions.prediction_main_4hr import fetch_latest_prediction as fourhrpredictions
import os

app = FastAPI()
views_router = APIRouter(tags=["Templates"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@views_router.get("/predictions", response_class=HTMLResponse, name="predictions")
async def landing_page(request: Request):
    four_hours_prediction = await fourhrpredictions()
    twelve_hours_prediction = await twelvehrpredictions()
    
    return templates.TemplateResponse("Predictions.html", 
        {
            "request": request,
            "fhr_pdts": four_hours_prediction,
            "twl_hr_pdts": twelve_hours_prediction,
        }
    )

@views_router.get("/accuracy", response_class=HTMLResponse, name="accuracy")
async def landing_page(request: Request):
    return templates.TemplateResponse("Accuracy.html",
        {
            "request": request,
            "title": "Welcome to CoinBeacon!"
        }
    )

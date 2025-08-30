from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
views_router = APIRouter(tags=["Templates"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@views_router.get("/rates", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("Predictions.html", {"request": request, "title": "Welcome to CoinBeacon!"})
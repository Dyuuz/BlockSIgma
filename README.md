#  BLOCKSIGMA FastAPI Application

This project is a cryptocurrency prediction system built with **FastAPI**, using **LSTM** and **XGBoost** models to generate 12-hour price predictions for active USDT trading pairs. It integrates with **Binance**, and **PostgreSQL**, with scheduled background tasks via **APScheduler**.

---

## 📦 Features

-  Scheduled price predictions every 12 hours
-  Real-time price tracking and evaluation every 30 seconds
-  Automatic cleanup of disabled/inactive crypto assets
-  Machine Learning: LSTM + XGBoost with RSI & MACD indicators
-  Timezone-aware scheduling with fallback to UTC
-  Environment variable support via `.env`
-  Organized with MVC pattern for scalability

---

## 📁 Project Structure

app/
├── database/ # Async DB connection

├── models/ # SQLAlchemy ORM models

├── schema/ # Pydantic schemas for validation

├── routers/ # FastAPI routers (users, predictions)

├── views/

│ └── predictions/ # LSTM, XGBoost, hybrid prediction logic

├── config.py # Configuration from .env or defaults

main.py # Entry point with scheduler and routes


---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mytradegenius.git
cd mytradegenius

### 2. Install Dependencies

pip install -r requirements.txt

### 3. Create .env File

## Run the App
uvicorn main:app --reload

Endpoints

➤ GET /price/latest-predictions
Returns the latest prediction results with readable timestamps.

{
    "asset_name": "1000CAT",
    "symbol": "1000CAT",
    "current_price": 0.00749,
    "price_at_predicted_time": 0.00742,
    "predicted_price": 0.00727689,
    "price_difference_currently": -2.85,
    "price_difference_at_predicted_time": -1.93,
    "current_status": true,
    "prediction_status": "No action",
    "predicted_time": "July 15 25, 01:20 PM UTC+00",
    "expiry_time": "July 16 25, 01:20 AM UTC+00",
    "achievement": "Not Reached",
    "time_reached": "Not Reached",
    "price_change_status": false
}

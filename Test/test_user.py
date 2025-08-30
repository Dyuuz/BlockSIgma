# tests/test_user.py
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

@pytest.mark.asyncio
async def test_create_and_read_user(initialized_app):
    # Create an ASGITransport that wraps your FastAPI app
    transport = ASGITransport(app=initialized_app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a user
        resp = await ac.post("/users/", json={"name":"Alice","email":"alice_joana@example.com"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Alice"

        # Read it back
        resp2 = await ac.get(f"/users/{data['id']}")
        assert resp2.status_code == 200
        assert resp2.json()["email"] == "alice_joana@example.com"

# tests/test_predictions.py
import pytest
from httpx import AsyncClient, ASGITransport
from decimal import Decimal
from datetime import datetime, timedelta

from app.main import app

@pytest.mark.asyncio
async def test_create_and_read_prediction(initialized_app):
    # wrap the FastAPI app in an ASGI transport
    transport = ASGITransport(app=initialized_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # prepare a sample payload
        now = datetime.utcnow()
        payload = {
            "asset_name": "Bitcoin",
            "symbol": "BTCUSD",
            "current_price": str(Decimal("30000.50")),
            "price_change_status": True,
            "price_at_predicted_time": str(Decimal("30500.75")),
            "predicted_price": str(Decimal("31000.25")),
            "price_difference_currently": str(Decimal("500.25")),
            "price_difference_at_predicted_time": str(Decimal("1000.75")),
            "current_status": False,
            "prediction_status": True,
            "predicted_time": (now + timedelta(days=1)).isoformat() + "Z",
            "expiry_time":   (now + timedelta(days=2)).isoformat() + "Z"
        }

        # CREATE
        resp = await ac.post("/predictions/", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # verify some fields
        assert data["asset_name"] == payload["asset_name"]
        assert data["symbol"] == payload["symbol"]
        assert data["prediction_status"] is True
        pred_id = data["id"]

        # READ
        resp2 = await ac.get(f"/predictions/{pred_id}")
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json()
        assert data2["id"] == pred_id
        assert data2["asset_name"] == "Bitcoin"
        assert Decimal(data2["current_price"]) == Decimal("30000.50")


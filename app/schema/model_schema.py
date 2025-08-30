# app/schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from typing import Optional
from datetime import datetime


# ─── Symbol Schemas ────────────────────────────────────────────────────────────

class SymbolBase(BaseModel):
    symbol: str


class SymbolCreate(SymbolBase):
    pass


class SymbolRead(SymbolBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ─── Prediction Schemas for 12hr ────────────────────────────────────────────────────────

class PredictionBase_12hr(BaseModel):
    asset_name: str
    symbol: str
    current_price: float
    price_at_predicted_time: float
    predicted_price: float
    price_difference_currently: float
    price_difference_at_predicted_time: float
    current_status: bool
    prediction_status: str
    predicted_time: datetime
    expiry_time: datetime
    price_change_status: bool
    achievement: Optional[str] = "Not Reached"
    time_reached: Optional[datetime] = None
    dynamic_tp: float
    dynamic_sl: float
    rrr: float
    sl_status: Optional[bool] = None

    model_config = {
        "from_attributes": True
    }


class PredictionCreate(PredictionBase_12hr):
    pass


class PredictionRead(PredictionBase_12hr):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ─── Prediction Schemas for 4hr────────────────────────────────────────────────────────

class PredictionBase_4hr(BaseModel):
    asset_name: str
    symbol: str
    current_price: float
    price_at_predicted_time: float
    predicted_price: float
    price_difference_currently: float
    price_difference_at_predicted_time: float
    current_status: bool
    prediction_status: str
    predicted_time: datetime
    expiry_time: datetime
    price_change_status: bool
    achievement: Optional[str] = "Not Reached"
    time_reached: Optional[datetime] = None
    interval: Optional[str] = "4hr"
    dynamic_tp: float
    dynamic_sl: float
    rrr: float
    sl_status: Optional[bool] = None

    model_config = {
        "from_attributes": True
    }


class PredictionCreate(PredictionBase_4hr):
    pass


class PredictionRead(PredictionBase_4hr):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ─── User Schemas ──────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True

# ─── BaseSummary Schemas ──────────────────────────────────────────────────────────────

class BaseSummaryCreate(BaseModel):
    from_: datetime = Field(..., alias="from")
    to: Optional[datetime] = None
    number_of_predictions: int
    accuracy: int
    details: Optional[List[Dict[str, Any]]] = None

    class Config:
        allow_population_by_field_name = True

class TwelveHoursSummaryCreate(BaseSummaryCreate):
    pass

class TwelveHoursBuySummaryCreate(BaseSummaryCreate):
    pass

class FourHoursSummaryCreate(BaseSummaryCreate):
    pass

class FourHoursBuySummaryCreate(BaseSummaryCreate):
    pass

# ─── Email Schemas ──────────────────────────────────────────────────────────────

class EmailSchema(BaseModel):
    email: EmailStr
    country: str
    timeframe: str
    name: str | None = None
    
    
class Candle(BaseModel):
    """Represents a single candlestick data point."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SignalRequest(BaseModel):
    """Request model for generating a signal."""
    token: str # e.g., "BTCUSDT", "ETHUSDT"
    
    


# ─── Signal Schemas────────────────────────────────────────────────────────
class SignalBase(BaseModel):
    symbol: str
    signal_type: str
    strength: float
    rsi: Optional[float] = None
    ema9: Optional[float] = None
    ema21: Optional[float] = None
    volatility_pct: float
    last_signal: str
    name: Optional[str] = None
    current_signal: Optional[str] = None
    user_ip: Optional[str] = None
    last_buy: Optional[datetime] = None
    last_buy_price: Optional[float] = None
    last_sell: Optional[datetime] = None
    last_sell_price: Optional[float] = None
    last_hold: Optional[datetime] = None
    last_hold_price: Optional[float] = None
    last_exit: Optional[datetime] = None
    last_exit_price: Optional[float] = None
    price: float
    updated_at: datetime
    timestamp: datetime
    
    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime, _info):
        return dt.strftime("%B %d %y, %I:%M %p UTC+00")
    
    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.strftime("%B %d %y, %I:%M %p UTC+00")
    
    @field_serializer("last_buy")
    def serialize_last_buy(self, dt: datetime | None, _info):
        if dt is None:
            return None  # or "Not Available", depending on your API contract
        return dt.strftime("%B %d %y, %I:%M %p UTC+00")
    
    @field_serializer("last_sell")
    def serialize_last_sell(self, dt: datetime | None, _info):
        if dt is None:
            return None  # or "Not Available", depending on your API contract
        return dt.strftime("%B %d %y, %I:%M %p UTC+00")

class Signal(SignalBase):
    id: str
    model_config = ConfigDict(from_attributes=True)
    
    
class BinancePriceBase(BaseModel):
    id: int
    asset: str
    current_price: float
    last_updated: datetime
    
    @field_serializer("last_updated")
    def serialize_last_updated(self, dt: datetime | None, _info):
        if dt is None:
            return None  # or "Not Available", depending on your API contract
        return dt.strftime("%B %d %y, %I:%M %p UTC+00")
    
    
    


# app/models.py
from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    String,
    Integer,
    Float,
    Numeric,
    Boolean,
    DateTime,
    func,
    JSON,
)
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy import String, Float, DateTime, Boolean
import uuid
from datetime import datetime



class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(Text, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions_v3"

    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(Text, nullable=False, unique=True, index=True)
    symbol = Column(Text, nullable=False, unique=True, index=True)

    current_price = Column(Numeric, nullable=False)
    price_change_status = Column(Boolean, nullable=False)
    price_at_predicted_time = Column(Numeric, nullable=False)
    predicted_price = Column(Numeric, nullable=False)
    price_difference_currently = Column(Numeric, nullable=False)
    price_difference_at_predicted_time = Column(Numeric, nullable=False)
    current_status = Column(Boolean, nullable=False)
    prediction_status = Column(Text, nullable=False)

    predicted_time = Column(DateTime(timezone=True), nullable=False)
    expiry_time = Column(DateTime(timezone=True), nullable=False)

    achievement = Column(Text, nullable=True, index=True)
    time_reached = Column(DateTime(timezone=True), nullable=True)

    dynamic_tp = Column(Numeric, nullable=True)
    dynamic_sl = Column(Numeric, nullable=True)
    rrr = Column(Numeric, nullable=True)

    sl_status = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())

    def as_dict(self, exclude: set[str] = {"id", "created_at"}) -> dict:
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
            if col.name not in exclude
        }


class Prediction4hr(Base):
    __tablename__ = "predictions_v3_4hr"

    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(Text, nullable=False, unique=True, index=True)
    symbol = Column(Text, nullable=False, unique=True, index=True)

    current_price = Column(Numeric, nullable=False)
    price_change_status = Column(Boolean, nullable=False)
    price_at_predicted_time = Column(Numeric, nullable=False)
    predicted_price = Column(Numeric, nullable=False)
    price_difference_currently = Column(Numeric, nullable=False)
    price_difference_at_predicted_time = Column(Numeric, nullable=False)
    current_status = Column(Boolean, nullable=False)
    prediction_status = Column(Text, nullable=False)

    predicted_time = Column(DateTime(timezone=True), nullable=False)
    expiry_time = Column(DateTime(timezone=True), nullable=False)

    achievement = Column(Text, nullable=True, index=True)
    time_reached = Column(DateTime(timezone=True), nullable=True)

    interval = Column(Text, nullable=False, index=True, default="4hr")

    dynamic_tp = Column(Numeric, nullable=True)
    dynamic_sl = Column(Numeric, nullable=True)
    rrr = Column(Numeric, nullable=True)

    sl_status = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())

    def as_dict(self, exclude: set[str] = {"id", "created_at"}) -> dict:
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
            if col.name not in exclude
        }


class TwelveHoursSummary(Base):
    __tablename__ = "twelve_hours_summary"

    id = Column(Integer, primary_key=True, index=True)
    from_ = Column(DateTime(timezone=True), nullable=False, unique=True)
    to = Column(DateTime(timezone=True), nullable=False)
    number_of_predictions = Column(Integer, nullable=False)
    accuracy = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())


class TwelveHoursBuySummary(Base):
    __tablename__ = "twelve_hours_buy_summary"

    id = Column(Integer, primary_key=True, index=True)
    from_ = Column(DateTime(timezone=True), nullable=False, unique=True)
    to = Column(DateTime(timezone=True), nullable=False)
    number_of_predictions = Column(Integer, nullable=False)
    accuracy = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())


class FourHoursSummary(Base):
    __tablename__ = "four_hours_summary"

    id = Column(Integer, primary_key=True, index=True)
    from_ = Column(DateTime(timezone=True), nullable=False, unique=True)
    to = Column(DateTime(timezone=True), nullable=False)
    number_of_predictions = Column(Integer, nullable=False)
    accuracy = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())


class FourHoursBuySummary(Base):
    __tablename__ = "four_hours_buy_summary"

    id = Column(Integer, primary_key=True, index=True)
    from_ = Column(DateTime(timezone=True), nullable=False, unique=True)
    to = Column(DateTime(timezone=True), nullable=False)
    number_of_predictions = Column(Integer, nullable=False)
    accuracy = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True),
                        nullable=False, server_default=func.now())


class Signal(Base):
    __tablename__ = "signals"  # Name of your table in PostgreSQL

    # Existing fields from previous discussions
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(
        uuid.uuid4()))  # Changed to String for UUID
    # Assuming symbol is unique for each signal
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    # This maps to 'signal_type' from interpreted_signal
    signal_type: Mapped[str] = mapped_column(String)
    strength: Mapped[float] = mapped_column(Float)
    rsi: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True)  # rsi_val
    ema9: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ema21: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_pct: Mapped[float] = mapped_column(Float, default=0.0)
    last_signal: Mapped[str] = mapped_column(
        String, default="")  # This seems like a derived field

    # Fields from your updated response model (from image) and sample data
    name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True)  # token["name"]
    current_signal: Mapped[Optional[str]] = mapped_column(
        String, nullable=True)  # "signal" from image
    user_ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_buy: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    last_buy_price: Mapped[Optional[float]
                           ] = mapped_column(Float, nullable=True)
    last_sell: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    last_sell_price: Mapped[Optional[float]
                            ] = mapped_column(Float, nullable=True)
    last_hold: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    last_hold_price: Mapped[Optional[float]
                            ] = mapped_column(Float, nullable=True)
    last_exit: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    last_exit_price: Mapped[Optional[float]
                            ] = mapped_column(Float, nullable=True)
    # 'current_price' from your sample data, 'price' in image
    price: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ts_iso from image
    timestamp: Mapped[datetime] = mapped_column(
        DateTime)  # ts_iso from sample data


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    
    
    
class BinancePrice(Base):
    __tablename__ = 'binanceprice'
    
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String, index=True)
    current_price = Column(Float, index=True, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


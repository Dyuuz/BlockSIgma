import httpx
from app.schema.model_schema import PredictionCreate
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from binance.client import Client
import xgboost as xgb
from datetime import datetime, timezone, timedelta
import requests
import random
from binance.exceptions import BinanceAPIException
import os
import re
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
import time
import asyncio

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)


def fetch_symbol_name_map() -> dict[str, str]:
    """
    Fetches a mapping of SYMBOL → Coin Name from CoinGecko.
    Returns uppercase symbol keys for lookup like: { 'BTC': 'Bitcoin', 'ETH': 'Ethereum' }
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        # async with httpx.AsyncClient(timeout=10.0) as client:
        response = requests.get(url)
        response.raise_for_status()
        coins = response.json()
        return {coin["symbol"].upper(): coin["name"] for coin in coins}
    except Exception as e:
        print(f"[✖] Failed to fetch CoinGecko symbol map: {e}")
        return {}


def main_model(asset_chunk_type, symbols, symbol_to_name):
    """
    Runs price prediction for a given chunk of asset symbols using LSTM.

    - Fetches recent price data and calculates technical indicators.
    - Trains an LSTM model to predict future prices for each symbol.
    - Compares predicted price to current market price to determine prediction and status.
    - Builds and returns a list of prediction dictionaries for database storage.

    Used to generate 12-hour predictions for asset chunks in a scheduled and batched process.
    """
    print(f"Fetching Binance data... for {asset_chunk_type}")

    now = datetime.now()
    print(f"Starting 4hr Prediction at.... {now}")

    predicted_prices = []

    url = "https://api.binance.com/api/v3/ticker/24hr"
    resp = requests.get(url)
    resp.raise_for_status()
    tickers = resp.json()

    price_map = {item['symbol']: item['lastPrice'] for item in tickers}

    symbol_names = fetch_symbol_name_map()
    for symbol in symbols:
        try:
            asset_name = re.sub(r"\s*USDT$", "", symbol, flags=re.IGNORECASE)
            asset_alt_names = symbol_to_name.get(
                asset_name) or symbol_names.get(asset_name) or asset_name
            quote = "USDT"
            df = fetch_binance_ohlcv(symbol=symbol+quote)
            df = add_indicators(df)

            # Scale close prices for LSTM
            scaler = MinMaxScaler()
            close_scaled = scaler.fit_transform(df[['close']].values)

            lstm_model, X_lstm, y_lstm = train_lstm_model_scaled(close_scaled)
            lstm_pred_scaled = lstm_model.predict(X_lstm[-1].reshape(1, 10, 1))
            lstm_pred_real = scaler.inverse_transform(
                [[lstm_pred_scaled.flatten()[0]]])[0][0]
            predicted_price = float(round(lstm_pred_real, 8))

            # Get Symbol Price
            current_price = float(price_map.get(symbol+quote))
            if current_price is None:
                print(f"⚠️ No price found for {symbol}")
                continue

            current_price = round(current_price, 8)
            price_change_status = True if current_price > predicted_price else False

            # percentage difference for price_difference_currently & price_difference_at_predicted_time
            price_difference_currently = ((current_price - current_price) / current_price) * 100
            price_difference_currently = round(price_difference_currently, 3)

            price_difference_when_predicted = ((predicted_price - current_price) / current_price) * 100
            price_difference_when_predicted = round(price_difference_when_predicted, 3)

            # relative difference (as a percentage of the predicted price)
            current_stat = ((current_price - predicted_price) / predicted_price) * 100
            current_stat = round(current_stat, 2)

            if current_stat >= 1.2:
                current_status = True
            else:
                current_status = False

            # relative difference (as a percentage of the predicted price)
            prediction_stat = ((predicted_price -current_price) / current_price) * 100
            prediction_stat = round(prediction_stat, 2)

            if prediction_stat >= 1.2:
                prediction_status = "Buy"
            else:
                prediction_status = "No action"

            achievement = "Not Reached"

            adjustment_factor = float(0.6)
            dynamic_tp = float(price_difference_when_predicted) * 0.90
            dynamic_sl = ((predicted_price - current_price) / current_price) * adjustment_factor * 100
            rrr = dynamic_tp / dynamic_sl if dynamic_sl != 0 else 0
            
            now =  datetime.now(timezone.utc)
            expiry = now + timedelta(hours=4)
            
            data = {
                "asset_name": f"{asset_alt_names}",
                "symbol": f"{asset_name}",
                "current_price": round(current_price, 8),
                "price_change_status": price_change_status,
                "price_at_predicted_time": round(current_price, 8),
                "predicted_price": round(predicted_price, 8),
                "price_difference_currently": round(price_difference_currently, 3),
                "price_difference_at_predicted_time": round(price_difference_when_predicted, 3),
                "current_status": current_status,
                "prediction_status": prediction_status,
                "predicted_time": now,
                "expiry_time": expiry,
                "achievement": achievement,
                "time_reached": None,
                "interval": '4hr',
                "dynamic_tp":  round(dynamic_tp, 3),
                "dynamic_sl": round(dynamic_sl, 3),
                "rrr": round(rrr, 2),
                "sl_status": None,
            }
            print(f"4hr Prediction: {data}")

            predicted_prices.append(data)

        except Exception as e:
            print(f"Error with {symbol}: {e}")

        # time.sleep(2)

    end = datetime.now()
    print(f"Ending 4hr Prediction at.... {end}")
    print(f"prices length for 4hr Prediction.... {len(predicted_prices)}")

    return predicted_prices


def fetch_binance_ohlcv(symbol, interval='30m', lookback='475 hours ago UTC', retries=3, sleep_sec=1):
    print(f"Fetching OHLCV for {symbol}...")

    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    columns_needed = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    for attempt in range(retries):
        try:
            kline_data = client.get_historical_klines(
                symbol, interval, lookback)
            break
        except BinanceAPIException as e:
            print(f"[{symbol}] Attempt {attempt+1}: BinanceAPIException - {e}")
        except Exception as e:
            print(f"[{symbol}] Attempt {attempt+1}: Unexpected error - {e}")
        time.sleep(sleep_sec + random.uniform(0.5, 1.5))  # Add jitter
    else:
        print(f"[{symbol}] Failed to fetch after {retries} retries.")
        return pd.DataFrame(columns=columns_needed)

    # If no data returned
    if not kline_data:
        return pd.DataFrame(columns=columns_needed)

    # Build DataFrame
    df = pd.DataFrame(kline_data, columns=columns)[columns_needed]

    # Convert timestamp to datetime and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Convert to lower precision to reduce memory
    df = df.astype({
        'open': 'float32',
        'high': 'float32',
        'low': 'float32',
        'close': 'float32',
        'volume': 'float32'
    })

    return df


def add_indicators(df):
    df['close'] = df['close'].astype(float)
    df['rsi'] = RSIIndicator(close=df['close']).rsi()
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df.dropna(inplace=True)
    return df


def create_lstm_dataset_scaled(data, look_back=10):
    X, y = [], []
    for i in range(len(data) - look_back - 1):
        X.append(data[i:(i + look_back), 0])
        y.append(data[i + look_back, 0])
    return np.array(X), np.array(y)


def train_lstm_model_scaled(scaled_series):
    X, y = create_lstm_dataset_scaled(scaled_series, look_back=10)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    model = Sequential()
    model.add(Input(shape=(X.shape[1], 1)))  # Clean input declaration
    model.add(LSTM(50))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)
    return model, X, y


def train_xgboost(df):
    features = ['rsi', 'macd', 'macd_signal']
    df['future_close'] = df['close'].shift(-1)
    df.dropna(inplace=True)
    X = df[features]
    y = df['future_close']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False)
    model = xgb.XGBRegressor()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    print("XGBoost RMSE:", np.sqrt(mean_squared_error(y_test, preds)))
    return model


if __name__ == "__main__":
    print(main_model('Asset Chunk 1', ["BTCUSDT", "ETHUSDT"]))

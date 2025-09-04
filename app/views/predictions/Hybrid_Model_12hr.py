import os
import re
import time
import random
import requests
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, LSTM, Dense
from tensorflow.keras import backend as K

from ta.momentum import RSIIndicator
from ta.trend import MACD
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
import xgboost as xgb
from app.utils.mem_logger import log_memory

from binance.client import Client
from binance.exceptions import BinanceAPIException

# Binance client
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)

# LSTM: single global model + fixed signature
TIMESTEPS = 10
FEATURES = 1
EPOCHS = 10
BATCH_SIZE = 32

def _build_reusable_model():
    x = Input(shape=(TIMESTEPS, FEATURES))
    h = LSTM(50)(x)
    y = Dense(1)(h)
    m = Model(x, y)
    m.compile(optimizer="adam", loss="mean_squared_error")

    # Predict fn with fixed signature to avoid retracing
    @tf.function(input_signature=[tf.TensorSpec(shape=[None, TIMESTEPS, FEATURES], dtype=tf.float32)])
    def _predict_fn(x_in):
        return m(x_in, training=False)

    return m, _predict_fn

GLOBAL_MODEL, _PREDICT_FN = _build_reusable_model()

def _reinit_model_weights(model: Model):
    """Reset weights without rebuilding graphs."""
    for layer in model.layers:
        # handle common dense/recurrent weights
        for attr in ("kernel", "recurrent_kernel", "bias"):
            w = getattr(layer, attr, None)
            init = getattr(layer, f"{attr}_initializer", None)
            if w is not None and init is not None:
                w.assign(tf.keras.initializers.get(init)(w.shape, dtype=w.dtype))


# Utilities
def _normalize_to_usdt_pair(symbol: str) -> tuple[str, str]:
    """Accepts 'BTC' or 'BTCUSDT' → returns ('BTC', 'BTCUSDT')."""
    base = re.sub(r"USDT$", "", symbol, flags=re.IGNORECASE)
    pair = base + "USDT"
    return base, pair


def fetch_symbol_name_map() -> dict[str, str]:
    """
    Fetches a mapping of SYMBOL → Coin Name from CoinGecko.
    Returns uppercase symbol keys for lookup like: { 'BTC': 'Bitcoin', 'ETH': 'Ethereum' }
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        coins = resp.json()
        return {coin["symbol"].upper(): coin["name"] for coin in coins}
    except Exception as e:
        print(f"[✖] Failed to fetch CoinGecko symbol map: {e}")
        return {}

# Data fetching / features
def fetch_binance_ohlcv(symbol, interval='1h', lookback='500 hours ago UTC', retries=3, sleep_sec=1):
    print(f"Fetching OHLCV for {symbol}...")

    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    columns_needed = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    for attempt in range(retries):
        try:
            kline_data = client.get_historical_klines(symbol, interval, lookback)
            break
        except BinanceAPIException as e:
            print(f"[{symbol}] Attempt {attempt+1}: BinanceAPIException - {e}")
        except Exception as e:
            print(f"[{symbol}] Attempt {attempt+1}: Unexpected error - {e}")
        time.sleep(sleep_sec + random.uniform(0.5, 1.5))  # jitter
    else:
        print(f"[{symbol}] Failed to fetch after {retries} retries.")
        return pd.DataFrame(columns=columns_needed)

    if not kline_data:
        return pd.DataFrame(columns=columns_needed)

    df = pd.DataFrame(kline_data, columns=columns)[columns_needed]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # compact dtypes
    df = df.astype({
        'open': 'float32',
        'high': 'float32',
        'low': 'float32',
        'close': 'float32',
        'volume': 'float32'
    })
    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['close'] = df['close'].astype('float32')
    df['rsi'] = RSIIndicator(close=df['close']).rsi().astype('float32')
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd().astype('float32')
    df['macd_signal'] = macd.macd_signal().astype('float32')
    df.dropna(inplace=True)
    return df

def create_lstm_dataset_scaled(data: np.ndarray, look_back=TIMESTEPS):
    X, y = [], []
    for i in range(len(data) - look_back - 1):
        X.append(data[i:(i + look_back), 0])
        y.append(data[i + look_back, 0])
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    return X, y


def _train_and_predict_scaled_REUSE(scaled_series: np.ndarray) -> float:
    """
    Reuse GLOBAL_MODEL. Reset weights, fit briefly, predict last step.
    Returns a **scaled** prediction value (in [0,1] scale).
    """
    # Build dataset with *fixed* shapes and dtypes
    X, y = create_lstm_dataset_scaled(scaled_series, look_back=TIMESTEPS)
    
    if X.shape[0] < 2:
        # not enough history: fallback to last observed scaled value
        return float(scaled_series[-1, 0])

    X = X.reshape((X.shape[0], TIMESTEPS, FEATURES)).astype('float32')
    y = y.astype('float32')

    # Reset only weights (keep single graph & compiled functions)
    _reinit_model_weights(GLOBAL_MODEL)

    # Fit quickly; keep epochs small to reduce time/memory
    GLOBAL_MODEL.fit(X, y, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)

    # Predict last window with a stable signature (prevents retracing)
    x_last = tf.convert_to_tensor(X[-1:])
    yhat = _PREDICT_FN(x_last) # tf.Tensor
    return float(yhat.numpy().ravel()[0])


# XGBoost (unchanged)
def train_xgboost(df):
    features = ['rsi', 'macd', 'macd_signal']
    df = df.copy()
    df['future_close'] = df['close'].shift(-1)
    df.dropna(inplace=True)
    X = df[features]
    y = df['future_close']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    model = xgb.XGBRegressor()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    print("XGBoost RMSE:", np.sqrt(mean_squared_error(y_test, preds)))
    return model


# Main Job (reuses single model)
def main_model(asset_chunk_type, symbols, symbol_to_name):
    """
    Runs price prediction for a given chunk of asset symbols using a single
    reusable LSTM model (no per-symbol rebuilds).
    """
    print(f"Fetching Binance data... for {asset_chunk_type}")

    start = datetime.now()
    print(f"Starting 12hr Prediction at.... {start}")

    predicted_prices = []

    # Preload current prices (map like {'BTCUSDT': '12345.67', ...})
    url = "https://api.binance.com/api/v3/ticker/24hr"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    tickers = resp.json()
    price_map = {item['symbol']: item['lastPrice'] for item in tickers}

    symbol_names_global = fetch_symbol_name_map()

    for user_symbol in symbols:
        
        try:
            log_memory("4hr Current memory usage on model training")
            base, pair = _normalize_to_usdt_pair(user_symbol)
            
            # asset display name
            asset_alt_names = (
                symbol_to_name.get(base) or
                symbol_names_global.get(base) or
                base
            )

            # Data + indicators
            df = fetch_binance_ohlcv(symbol=pair, interval='1h', lookback='500 hours ago UTC')
            if df.empty:
                print(f"⚠️ No OHLCV for {pair}")
                continue
            df = add_indicators(df)

            # Scale close prices (float32 to reduce memory)
            scaler = MinMaxScaler()
            close_scaled = scaler.fit_transform(df[['close']].values.astype('float32'))

            # --- Reuse single model for training & prediction ---
            lstm_pred_scaled_val = _train_and_predict_scaled_REUSE(close_scaled)

            # inverse scale
            lstm_pred_real = scaler.inverse_transform([[lstm_pred_scaled_val]])[0][0]
            predicted_price = float(round(lstm_pred_real, 8))

            # Current price
            cp_str = price_map.get(pair)
            if cp_str is None:
                print(f"⚠️ No price found for {pair}")
                continue
            current_price = round(float(cp_str), 8)

            price_change_status = current_price > predicted_price

            # percentage difference for price_difference_currently & price_difference_at_predicted_time
            price_difference_currently = 0.0  # (cur - cur)/cur → 0
            price_difference_when_predicted = ((predicted_price - current_price) / current_price) * 100 if current_price else 0.0
            price_difference_when_predicted = round(price_difference_when_predicted, 3)

            # relative difference (%) of current vs predicted
            current_stat = ((current_price - predicted_price) / predicted_price) * 100 if predicted_price else 0.0
            current_stat = round(current_stat, 2)
            current_status = current_stat >= 1.2

            # relative difference (%) of prediction vs current
            prediction_stat = ((predicted_price - current_price) / current_price) * 100 if current_price else 0.0
            prediction_stat = round(prediction_stat, 2)
            prediction_status = "Buy" if prediction_stat >= 1.2 else "No action"

            achievement = "Not Reached"

            # risk metrics
            adjustment_factor = 0.6
            dynamic_tp = price_difference_when_predicted * 0.90
            dynamic_sl = ((predicted_price - current_price) / current_price) * adjustment_factor * 100 if current_price else 0.0
            rrr = dynamic_tp / dynamic_sl if dynamic_sl else 0

            now_utc = datetime.now(timezone.utc)
            expiry = now_utc + timedelta(hours=12)

            data = {
                "asset_name": f"{asset_alt_names}",
                "symbol": f"{base}",
                "current_price": round(current_price, 8),
                "price_change_status": price_change_status,
                "price_at_predicted_time": round(current_price, 8),
                "predicted_price": round(predicted_price, 8),
                "price_difference_currently": round(price_difference_currently, 3),
                "price_difference_at_predicted_time": round(price_difference_when_predicted, 3),
                "current_status": current_status,
                "prediction_status": prediction_status,
                "predicted_time": now_utc,
                "expiry_time": expiry,
                "achievement": achievement,
                "time_reached": None,
                "dynamic_tp": round(dynamic_tp, 3),
                "dynamic_sl": round(dynamic_sl, 3),
                "rrr": round(rrr, 2),
                "sl_status": None,
            }
            print(f"12hr Prediction: {data}")

            predicted_prices.append(data)

        except Exception as e:
            print(f"Error with {user_symbol}: {e}")
            
        finally:
            df = None
            scaler = None
            close_scaled = None

            # No clear_session() here — we reuse the single model/graph.

            log_memory(f"12hr Current memory usage at the end of {user_symbol} model training")

    end = datetime.now()
    print(f"Ending 12hr Prediction at.... {end}")
    print(f"prices length for 12hr Prediction.... {len(predicted_prices)}")

    # NOTE:
    # - K.clear_session() was not called here so the single model
    #   stays warm across invocations in the same process.
    # - Clear TF only once per job (keeps process RSS stable within job; releases at end)
    
    try:
        K.clear_session()
    except Exception:
        pass
    finally:
        gc.collect()

    return predicted_prices


# __main__: local test
if __name__ == "__main__":
    print(main_model('Asset Chunk 1', ["BTCUSDT", "ETHUSDT"], symbol_to_name={}))

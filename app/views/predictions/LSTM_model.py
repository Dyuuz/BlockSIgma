import numpy as np
import pandas as pd
from binance.client import Client
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)


def get_all_predictions(asset_chunk_type, symbols):
    """

    """
    print(f"Fetching Binance data... for {asset_chunk_type}")

    now = datetime.now()
    print(f"Starting time.... {now}")

    predicted_prices = {}

    for symbol in symbols:
        try:
            df = get_binance_data(symbol=symbol)
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(df)

            seq_len = 60
            X, y = [], []
            for i in range(seq_len, len(scaled_data)):
                X.append(scaled_data[i-seq_len:i, 0])
                y.append(scaled_data[i, 0])
            X = np.array(X).reshape(-1, seq_len, 1)
            y = np.array(y)

            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(seq_len, 1)),
                LSTM(50),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mean_squared_error')
            model.fit(X, y, epochs=10, batch_size=32, verbose=0)

            input_seq = scaled_data[-seq_len:].reshape(1, seq_len, 1)
            for _ in range(12):
                pred = model.predict(input_seq, verbose=0)[0][0]
                input_seq = np.append(input_seq[0, 1:, 0], pred).reshape(1, seq_len, 1)

            predicted_price = scaler.inverse_transform(np.array([[pred]]))[0][0]
            predicted_price = float(round(predicted_price, 8))

            # Get current price of symbol
            current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
            current_price = round(current_price, 8)
            # print(f"Cuurent price: {current_price:.8f}")

            percentage_increase = ((predicted_price - current_price) / current_price) * 100
            print(f"% increase: {percentage_increase}")

            if percentage_increase >= 1.2:
                status = "⬆️"
            else:
                status = "🔻"
            
            predicted_prices[symbol] = {
                "current_price": f"{current_price:.8f}",
                "predicted_price": f"{predicted_price:.8f}",
                "status": status
            }

        except Exception as e:
            print(f"Error with {symbol}: {e}")
            
    end = datetime.now()
    print(f"Ending time.... {end}")

    return predicted_prices

def get_binance_data(symbol, interval='1h', lookback='7 days ago UTC'):
    from binance.client import Client
    import pandas as pd
    
    kline_data = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, lookback)
    df = pd.DataFrame(kline_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Ensures numeric columns are float and rounded to 8 decimals
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = df[col].astype(float).round(8)

    pd.set_option('display.float_format', '{:.8f}'.format)
    # print(df.head())

    return df[['close']]

if __name__ == "__main__":
    print("Starting prediction...")
    # asset = get_asset_chunks().get('Asset chunk 1')
    result = get_all_predictions('Asset chunk 1', symbols=["BTCUSDT", "SHIBUSDT"])
    print("Result:", result)
    # print(get_binance_data())

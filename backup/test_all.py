import pandas as pd
import yfinance as yf
import pickle
import numpy as np

def run():
    with open('ai_brain.pkl', 'rb') as f:
        model = pickle.load(f)
    
    df_symbols = pd.read_csv('nifty200_symbols.csv')
    symbols = df_symbols['Yahoo_Symbol'].tolist()
    
    print('Downloading data...')
    data = yf.download(symbols, period='6mo', group_by='ticker', threads=True, progress=False)
    
    trades = 0
    
    for symbol in symbols:
        try:
            df = data[symbol].copy()
            df.dropna(inplace=True)
            if len(df) < 50:
                continue
                
            vol_mean = df['Volume'].rolling(window=20).mean()
            vol_std = df['Volume'].rolling(window=20).std()
            df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
            
            df['Gap_Pct'] = (df['Open'] - df['High'].shift(1)) / df['High'].shift(1)
            
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df['ATR'] = true_range.rolling(window=14).mean()
            df['ATR_Pct'] = df['ATR'] / df['Close']
            
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI_14'] = 100 - (100 / (1 + rs))
            
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['Dist_EMA20'] = (df['Close'] - df['EMA_20']) / df['EMA_20']
            df['Dist_EMA50'] = (df['Close'] - df['EMA_50']) / df['EMA_50']
            df['Daily_Ret'] = df['Close'].pct_change()
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = macd - macd_signal
            
            bb_mid = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            bb_lower = bb_mid - (bb_std * 2)
            df['Dist_BBLower'] = (df['Close'] - bb_lower) / df['Close']
            
            df.dropna(inplace=True)
            if len(df) < 50:
                continue

            start_idx = max(0, len(df) - 65 - 15)
            for i in range(start_idx, len(df) - 15):
                row = df.iloc[i]
                features = pd.DataFrame([{
                    'Vol_ZScore': row['Vol_ZScore'],
                    'Gap_Pct': row['Gap_Pct'],
                    'ATR_Pct': row['ATR_Pct'],
                    'RSI_14': row['RSI_14'],
                    'Dist_EMA20': row['Dist_EMA20'],
                    'Dist_EMA50': row['Dist_EMA50'],
                    'Daily_Ret': row['Daily_Ret'],
                    'MACD_Hist': row['MACD_Hist'],
                    'Dist_BBLower': row['Dist_BBLower']
                }])
                prob = model.predict_proba(features)[0][1]
                if prob > 0.65:
                    trades += 1
        except Exception as e:
            pass

    print(f'Total trades found in last 3 months for all 200 stocks: {trades}')

run()

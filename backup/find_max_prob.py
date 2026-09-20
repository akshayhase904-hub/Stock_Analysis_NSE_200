import pandas as pd
import yfinance as yf
import numpy as np
import pickle

def compute_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

with open("ai_brain.pkl", "rb") as f:
    model = pickle.load(f)
    
df_symbols = pd.read_csv("nifty200_symbols.csv")
symbols = df_symbols["Yahoo_Symbol"].tolist()[:50]
data = yf.download(symbols, period="1y", group_by="ticker", threads=True, progress=False)

max_prob = 0
for symbol in symbols:
    df = data[symbol].copy() if len(symbols) > 1 else data.copy()
    df.dropna(inplace=True)
    if len(df) < 50: continue
    
    vol_mean = df['Volume'].rolling(window=20).mean()
    vol_std = df['Volume'].rolling(window=20).std()
    df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
    df['Gap_Pct'] = (df['Open'] - df['High'].shift(1)) / df['High'].shift(1)
    df['ATR'] = compute_atr(df, 14)
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
    
    df_clean = df.dropna().copy()
    if len(df_clean) == 0: continue
    
    features = df_clean[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret']]
    probs = model.predict_proba(features)[:, 1]
    
    if len(probs) > 0 and max(probs) > max_prob:
        max_prob = max(probs)

print(f"Max AI Confidence across 50 stocks for 1 year: {max_prob * 100:.2f}%")


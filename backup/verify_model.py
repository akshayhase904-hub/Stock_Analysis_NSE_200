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

def run_backtest():
    with open("ai_brain.pkl", "rb") as f:
        model = pickle.load(f)
        
    df_symbols = pd.read_csv("nifty200_symbols.csv")
    symbols = df_symbols["Yahoo_Symbol"].tolist()[:100] # Test on first 100 to save time
    
    print(f"Downloading 3 years of out-of-sample data for backtesting...")
    data = yf.download(symbols, period="3y", group_by="ticker", threads=True, progress=False)
    
    total_trades = 0
    wins = 0
    losses = 0
    
    for symbol in symbols:
        try:
            df = data[symbol].copy() if len(symbols) > 1 else data.copy()
            df.dropna(inplace=True)
            if len(df) < 50:
                continue
                
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
            
            # 7. MACD (Quantum Analytics)
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
            
            # 8. Bollinger Bands (Math Stats)
            df['BB_Mid'] = df['Close'].rolling(window=20).mean()
            df['BB_Std'] = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
            df['Dist_BBLower'] = (df['Close'] - df['BB_Lower']) / df['Close']
            
            df_clean = df.dropna().copy()
            if len(df_clean) == 0: continue
            
            features = df_clean[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret', 'MACD_Hist', 'Dist_BBLower']]
            probs = model.predict_proba(features)[:, 1]
            
            df_clean['AI_Prob'] = probs
            buy_signals = df_clean[df_clean['AI_Prob'] > 0.70]
            
            for idx in buy_signals.index:
                i = df.index.get_loc(idx)
                if i > len(df) - 16:
                    continue
                    
                entry_price = df.iloc[i]['Close']
                target_price = entry_price * 1.07
                sl_price = entry_price * 0.97
                
                hit_target = False
                hit_sl = False
                
                for j in range(1, 16):
                    future_high = df['High'].iloc[i + j]
                    future_low = df['Low'].iloc[i + j]
                    
                    if future_low <= sl_price:
                        hit_sl = True
                        break
                    if future_high >= target_price:
                        hit_target = True
                        break
                        
                if hit_target:
                    wins += 1
                    total_trades += 1
                elif hit_sl:
                    losses += 1
                    total_trades += 1
                else:
                    future_close = df['Close'].iloc[i + 15]
                    if future_close > entry_price:
                        wins += 1
                    else:
                        losses += 1
                    total_trades += 1
        except Exception as e:
            pass

    if total_trades > 0:
        win_rate = (wins / total_trades) * 100
        print("\n--- AI SYSTEM BACKTEST RESULTS (7-YEAR BRAIN) ---")
        print(f"Total AI Triggered Trades: {total_trades}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Strategy: +7% Target | -3% Stop Loss | >80% AI Confidence")
    else:
        print("No trades triggered at this confidence level.")

if __name__ == "__main__":
    run_backtest()

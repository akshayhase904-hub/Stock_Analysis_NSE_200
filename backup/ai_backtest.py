import pandas as pd
import numpy as np
import os
import pickle
import glob

def compute_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

def run_ai_backtest():
    with open("ai_brain.pkl", "rb") as f:
        model = pickle.load(f)
        
    csv_files = glob.glob("data/*.csv")
    
    total_trades = 0
    wins = 0
    losses = 0
    
    print(f"Backtesting over {len(csv_files)} historical stock files from 'data/'...")
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            if len(df) < 50:
                continue
                
            # Features
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
            
            df_clean = df.copy()
            df_clean.dropna(inplace=True)
            
            if len(df_clean) == 0: continue
            
            features = df_clean[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret']]
            probs = model.predict_proba(features)[:, 1]
            
            df_clean['AI_Prob'] = probs
            buy_signals = df_clean[df_clean['AI_Prob'] > 0.80]
            
            for idx in buy_signals.index:
                if idx > len(df) - 16:
                    continue # Not enough forward days to trace
                    
                entry_price = df.loc[idx, 'Close']
                target_price = entry_price * 1.07
                sl_price = entry_price * 0.97
                
                hit_target = False
                hit_sl = False
                
                for j in range(1, 16):
                    future_high = df.loc[idx + j, 'High']
                    future_low = df.loc[idx + j, 'Low']
                    
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
                    future_close = df.loc[idx + 15, 'Close']
                    if future_close > entry_price:
                        wins += 1
                    else:
                        losses += 1
                    total_trades += 1
                    
        except Exception as e:
            pass

    if total_trades > 0:
        win_rate = (wins / total_trades) * 100
        print("\n--- AI SYSTEM BACKTEST RESULTS (THRESHOLD > 80%) ---")
        print(f"Total AI Triggered Trades: {total_trades}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Strategy: +7% Target | -3% Stop Loss | 15 Day Max Hold")
    else:
        print("No trades triggered at this confidence level.")

if __name__ == "__main__":
    run_ai_backtest()


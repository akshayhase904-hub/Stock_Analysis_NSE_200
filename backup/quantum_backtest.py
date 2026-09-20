import pandas as pd
import yfinance as yf
import numpy as np

def compute_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

def run_backtest():
    print("Loading symbols...")
    df_symbols = pd.read_csv("nifty200_symbols.csv")
    symbols = df_symbols["Yahoo_Symbol"].tolist()
    
    print("Downloading historical data (2 years)...")
    data = yf.download(symbols, period="2y", group_by="ticker", threads=True, progress=False)
    
    total_trades = 0
    wins = 0
    losses = 0

    print("Running Quantum Breakaway Backtest...")
    for symbol in symbols:
        try:
            if len(symbols) > 1:
                df = data[symbol].copy()
            else:
                df = data.copy()
            
            df.dropna(inplace=True)
            if len(df) < 50: 
                continue
                
            # Volume Z-Score
            vol_mean = df['Volume'].rolling(window=20).mean()
            vol_std = df['Volume'].rolling(window=20).std()
            df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
            
            # Gap detection
            df['Gap_Up'] = df['Open'] > df['High'].shift(1)
            df['Gap_Pct'] = (df['Open'] - df['High'].shift(1)) / df['High'].shift(1)
            
            # ATR Volatility
            df['ATR'] = compute_atr(df, 14)
            df['ATR_Pct'] = df['ATR'] / df['Close']
            
            # Momentum
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI_14'] = 100 - (100 / (1 + rs))
            
            # Trend
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            in_trade = False
            entry_price = 0
            target = 0
            sl = 0
            days_held = 0
            
            for i in range(50, len(df)):
                row = df.iloc[i]
                
                if in_trade:
                    days_held += 1
                    if row['High'] >= target:
                        wins += 1
                        total_trades += 1
                        in_trade = False
                    elif row['Low'] <= sl:
                        losses += 1
                        total_trades += 1
                        in_trade = False
                    elif days_held >= 15:
                        total_trades += 1
                        if row['Close'] > entry_price:
                            wins += 1
                        else:
                            losses += 1
                        in_trade = False
                else:
                    # Quantum Breakaway Logic:
                    # 1. Exceptional Volume (Z-score > 2.5) -> Top 1% of volume events
                    # 2. Strong trend (Close > 20 EMA > 50 EMA)
                    # 3. Low underlying volatility (ATR < 2.5% of stock price) so 3% SL isn't hit by noise
                    # 4. RSI > 60 (strong momentum)
                    # 5. Gap up or massive green candle (Close > Open * 1.02)
                    
                    vol_anomoly = row['Vol_ZScore'] > 2.5
                    trend = row['Close'] > row['EMA_20'] > row['EMA_50']
                    low_volatility = row['ATR_Pct'] < 0.025
                    momentum = row['RSI_14'] > 60
                    strong_move = (row['Close'] > row['Open'] * 1.02) or (row['Gap_Up'] and row['Gap_Pct'] > 0.01)
                    
                    if vol_anomoly and trend and low_volatility and momentum and strong_move:
                        in_trade = True
                        entry_price = row['Close']
                        target = entry_price * 1.07
                        sl = entry_price * 0.97
                        days_held = 0
                                
        except Exception as e:
            pass

    print("\n" + "="*40)
    print("QUANTUM BREAKAWAY BACKTEST RESULTS")
    print("="*40)
    print(f"Total Trades Taken: {total_trades}")
    if total_trades > 0:
        win_rate = (wins / total_trades) * 100
        print(f"Wins: {wins} ({win_rate:.2f}%)")
        print(f"Losses: {losses} ({100-win_rate:.2f}%)")
    else:
        print("No trades triggered based on current logic.")

if __name__ == "__main__":
    run_backtest()


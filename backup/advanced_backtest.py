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
    time_exits = 0
    time_exit_wins = 0
    time_exit_losses = 0

    print("Running Advanced Quantitative Backtest...")
    for symbol in symbols:
        try:
            if len(symbols) > 1:
                df = data[symbol].copy()
            else:
                df = data.copy()
            
            df.dropna(inplace=True)
            if len(df) < 200: # Need more data for 200 EMA
                continue
                
            # 1. Advanced Trend Filter (20, 50, 200 EMAs)
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            
            # 2. RSI
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI_14'] = 100 - (100 / (1 + rs))
            
            # 3. Z-Score of Volume (Quantitative anomaly detection)
            vol_mean = df['Volume'].rolling(window=20).mean()
            vol_std = df['Volume'].rolling(window=20).std()
            df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
            
            # 4. Volatility Filter using ATR (Mathematics)
            df['ATR'] = compute_atr(df, 14)
            # If 3% of stock price is smaller than 1.5x ATR, 
            # it means daily noise will easily hit our SL. We avoid these.
            df['Noise_Threshold'] = df['ATR'] * 1.5
            
            in_trade = False
            entry_price = 0
            target = 0
            sl = 0
            days_held = 0
            
            for i in range(200, len(df)):
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
                        time_exits += 1
                        total_trades += 1
                        if row['Close'] > entry_price:
                            wins += 1
                            time_exit_wins += 1
                        else:
                            losses += 1
                            time_exit_losses += 1
                        in_trade = False
                else:
                    # QUANTITATIVE ENTRY LOGIC
                    # Strong uptrend across all timeframes
                    trend_up = row['Close'] > row['EMA_20'] > row['EMA_50'] > row['EMA_200']
                    
                    # Momentum is strong but not exhausted
                    momentum = 55 <= row['RSI_14'] <= 70
                    
                    # Volume is statistically significant (Z-score > 1.5 means top 6% of volume days)
                    vol_breakout = row['Vol_ZScore'] > 1.5
                    
                    # Math constraint: Only trade if 3% stop loss is larger than daily noise (1.5x ATR)
                    # This prevents getting stopped out by random daily fluctuations
                    three_percent_val = row['Close'] * 0.03
                    math_valid = three_percent_val > row['Noise_Threshold']
                    
                    if trend_up and momentum and vol_breakout and math_valid:
                        in_trade = True
                        entry_price = row['Close']
                        target = entry_price * 1.07
                        sl = entry_price * 0.97
                        days_held = 0
                                
        except Exception as e:
            pass

    print("\n" + "="*40)
    print("ADVANCED QUANTITATIVE BACKTEST RESULTS")
    print("="*40)
    print(f"Total Trades Taken: {total_trades}")
    if total_trades > 0:
        win_rate = (wins / total_trades) * 100
        print(f"Wins: {wins} ({win_rate:.2f}%)")
        print(f"Losses: {losses} ({100-win_rate:.2f}%)")
        print(f"  -> Trades exited by Time (15 days): {time_exits}")
        print(f"       Wins: {time_exit_wins} | Losses: {time_exit_losses}")
    else:
        print("No trades triggered based on current logic.")

if __name__ == "__main__":
    run_backtest()


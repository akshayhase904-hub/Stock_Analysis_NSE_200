import pandas as pd
import yfinance as yf
import numpy as np

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

    print("Running backtest for each symbol...")
    for symbol in symbols:
        try:
            if len(symbols) > 1:
                df = data[symbol].copy()
            else:
                df = data.copy()
            
            df.dropna(inplace=True)
            if len(df) < 50:
                continue
                
            # Indicators
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI_14'] = 100 - (100 / (1 + rs))
            
            df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()
            
            in_trade = False
            entry_price = 0
            target = 0
            sl = 0
            days_held = 0
            
            for i in range(50, len(df)):
                row = df.iloc[i]
                
                if in_trade:
                    days_held += 1
                    # Check exits
                    # Assuming we can hit target or SL intra-day based on High/Low
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
                    # Check entry conditions
                    if row['Close'] > row['EMA_20'] > row['EMA_50']:
                        if 45 <= row['RSI_14'] <= 65:
                            if row['Volume'] > row['VOL_SMA_20']:
                                in_trade = True
                                entry_price = row['Close']
                                target = entry_price * 1.07
                                sl = entry_price * 0.97
                                days_held = 0
                                
        except Exception as e:
            pass

    print("\n" + "="*40)
    print("BACKTEST RESULTS (Last 2 Years)")
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


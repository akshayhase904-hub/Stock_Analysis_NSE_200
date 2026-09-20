import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

ACTIVE_TRADES_FILE = "active_trades.csv"
COMPLETED_TRADES_FILE = "completed_trades.csv"

def init_db():
    if not os.path.exists(ACTIVE_TRADES_FILE):
        pd.DataFrame(columns=['Symbol', 'Entry Date', 'Entry Price', 'Target', 'Stop Loss']).to_csv(ACTIVE_TRADES_FILE, index=False)
    if not os.path.exists(COMPLETED_TRADES_FILE):
        pd.DataFrame(columns=['Symbol', 'Entry Date', 'Entry Price', 'Exit Date', 'Exit Price', 'Status', 'PnL']).to_csv(COMPLETED_TRADES_FILE, index=False)

def update_active_trades():
    init_db()
    active_df = pd.read_csv(ACTIVE_TRADES_FILE)
    if active_df.empty:
        return active_df, pd.DataFrame()
        
    symbols = active_df['Symbol'].unique().tolist()
    yfinance_symbols = [s + ".NS" for s in symbols]
    
    # Download last 30 days to cover any active trade
    data = yf.download(yfinance_symbols, period="1mo", group_by="ticker", progress=False)
    
    completed_trades = []
    remaining_active = []
    
    for _, trade in active_df.iterrows():
        symbol = trade['Symbol']
        yf_sym = symbol + ".NS"
        entry_date_str = trade['Entry Date']
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
        
        # If single symbol, yfinance returns flat dataframe
        df = data[yf_sym].copy()
            
        df = df.dropna()
        # Filter data from entry date onwards
        mask = df.index > pd.to_datetime(entry_date)
        future_df = df[mask]
        
        closed = False
        for idx, row in future_df.iterrows():
            # Check Stop Loss first
            if row['Low'] <= trade['Stop Loss']:
                completed_trades.append({
                    'Symbol': symbol,
                    'Entry Date': entry_date_str,
                    'Entry Price': trade['Entry Price'],
                    'Exit Date': idx.strftime("%Y-%m-%d"),
                    'Exit Price': trade['Stop Loss'],
                    'Status': 'Loss',
                    'PnL': round(((trade['Stop Loss'] - trade['Entry Price']) / trade['Entry Price']) * 100, 2)
                })
                closed = True
                break
            # Check Target
            elif row['High'] >= trade['Target']:
                completed_trades.append({
                    'Symbol': symbol,
                    'Entry Date': entry_date_str,
                    'Entry Price': trade['Entry Price'],
                    'Exit Date': idx.strftime("%Y-%m-%d"),
                    'Exit Price': trade['Target'],
                    'Status': 'Win',
                    'PnL': round(((trade['Target'] - trade['Entry Price']) / trade['Entry Price']) * 100, 2)
                })
                closed = True
                break
                
        if not closed:
            # Check if 15 days elapsed
            if len(future_df) >= 15:
                exit_row = future_df.iloc[14]
                exit_price = exit_row['Close']
                pnl = round(((exit_price - trade['Entry Price']) / trade['Entry Price']) * 100, 2)
                status = "Time Exit (Win)" if pnl > 0 else "Time Exit (Loss)"
                completed_trades.append({
                    'Symbol': symbol,
                    'Entry Date': entry_date_str,
                    'Entry Price': trade['Entry Price'],
                    'Exit Date': future_df.index[14].strftime("%Y-%m-%d"),
                    'Exit Price': round(exit_price, 2),
                    'Status': status,
                    'PnL': pnl
                })
                closed = True
                
        if not closed:
            remaining_active.append(trade)
            
    # Save back
    pd.DataFrame(remaining_active).to_csv(ACTIVE_TRADES_FILE, index=False)
    
    comp_df = pd.DataFrame(completed_trades)
    if not comp_df.empty:
        old_comp = pd.read_csv(COMPLETED_TRADES_FILE)
        new_comp = pd.concat([old_comp, comp_df], ignore_index=True)
        new_comp.to_csv(COMPLETED_TRADES_FILE, index=False)
        
    return pd.DataFrame(remaining_active), comp_df

def add_new_trades(new_trades):
    init_db()
    if not new_trades:
        return
    active_df = pd.read_csv(ACTIVE_TRADES_FILE)
    new_df = pd.DataFrame(new_trades)
    combined = pd.concat([active_df, new_df], ignore_index=True)
    combined.to_csv(ACTIVE_TRADES_FILE, index=False)

if __name__ == "__main__":
    init_db()
    print("Database Initialized.")

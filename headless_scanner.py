import pandas as pd
import yfinance as yf
import numpy as np
import os
import pickle
import requests
from trade_manager import update_active_trades, add_new_trades
from datetime import datetime

def compute_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

def run_headless_scan():
    print("Updating Active Trades...")
    active_df, comp_df = update_active_trades()
    
    msg = "?? *Daily AI Portfolio Update*\n\n"
    
    # Check if any trades just closed today
    if not comp_df.empty:
        # Only show trades that were completed TODAY (since last run)
        today_str = datetime.now().strftime("%Y-%m-%d")
        recent_comps = comp_df[comp_df['Exit Date'] == today_str]
        if not recent_comps.empty:
            msg += "? *Trades Closed Today*\n"
            for _, row in recent_comps.iterrows():
                icon = "?? Win" if "Win" in row['Status'] else "?? Loss"
                msg += f" {row['Symbol']}: {icon} ({row['PnL']}%)\n"
            msg += "\n"
    
    if not active_df.empty:
        msg += "?? *Live Ongoing Trades*\n"
        for _, row in active_df.iterrows():
            msg += f" {row['Symbol']} (Entry: ?{row['Entry Price']})\n"
        msg += "\n"

    print("Starting Headless AI Scan...")
    
    try:
        df_symbols = pd.read_csv("nifty200_symbols.csv")
        symbols = df_symbols["Yahoo_Symbol"].tolist()
    except Exception as e:
        print(f"Error loading symbols: {e}")
        return

    try:
        import gzip
        with gzip.open("ai_brain.pkl.gz", "rb") as f:
            ai_model = pickle.load(f)
    except Exception as e:
        print(f"Error loading AI model: {e}")
        return

    data = yf.download(symbols, period="6mo", group_by="ticker", threads=True, progress=False)

    picks = []
    
    current_date_str = datetime.now().strftime("%Y-%m-%d")

    for symbol in symbols:
        try:
            df = data[symbol].copy()
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
            if len(df) == 0: continue
            
            latest = df.iloc[-1]
            close = latest['Close']
            
            features = pd.DataFrame([{
                'Vol_ZScore': latest['Vol_ZScore'],
                'Gap_Pct': latest['Gap_Pct'],
                'ATR_Pct': latest['ATR_Pct'],
                'RSI_14': latest['RSI_14'],
                'Dist_EMA20': latest['Dist_EMA20'],
                'Dist_EMA50': latest['Dist_EMA50'],
                'Daily_Ret': latest['Daily_Ret'],
                'MACD_Hist': latest['MACD_Hist'],
                'Dist_BBLower': latest['Dist_BBLower']
            }])

            prob = ai_model.predict_proba(features)[0][1]
            
            # Use 0.65 threshold
            if prob > 0.65:
                # Also ensure we are not already active in this stock
                clean_symbol = symbol.replace('.NS', '')
                if active_df.empty or clean_symbol not in active_df['Symbol'].values:
                    target = close * 1.07
                    sl = close * 0.97
                    picks.append({
                        'Symbol': clean_symbol,
                        'Entry Date': current_date_str,
                        'Entry Price': round(close, 2),
                        'Target': round(target, 2),
                        'Stop Loss': round(sl, 2),
                        'Prob': round(prob * 100, 1)
                    })
        except Exception:
            pass

    picks.sort(key=lambda x: x['Prob'], reverse=True)
    picks = picks[:5] # Max 5 new picks per day
    
    if picks:
        msg += "?? *NEW PICKS TODAY*\n"
        db_new_trades = []
        for p in picks:
            msg += (f" *{p['Symbol']}*\n"
                    f"  Entry: ?{p['Entry Price']} | Target: ?{p['Target']} | SL: ?{p['Stop Loss']}\n"
                    f"  Confidence: {p['Prob']}%\n")
            
            db_new_trades.append({
                'Symbol': p['Symbol'],
                'Entry Date': p['Entry Date'],
                'Entry Price': p['Entry Price'],
                'Target': p['Target'],
                'Stop Loss': p['Stop Loss']
            })
        add_new_trades(db_new_trades)
    else:
        msg += "?? *NEW PICKS TODAY*: None\n"
        
    print("Final Message:\n", msg)

    # Send Telegram Message
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if tg_token and tg_chat_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        payload = {
            "chat_id": tg_chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload)
            if resp.status_code == 200:
                print("Telegram message sent successfully!")
            else:
                print(f"Failed to send Telegram: {resp.text}")
        except Exception as e:
            print(f"Error sending Telegram: {e}")
    else:
        print("Telegram credentials not found in environment. Skipping message.")

if __name__ == "__main__":
    run_headless_scan()

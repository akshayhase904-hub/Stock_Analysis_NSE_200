import pandas as pd
import joblib
import yfinance as yf

def test_thresholds():
    df_symbols = pd.read_csv("nifty200_symbols.csv")
    symbols = df_symbols["Yahoo_Symbol"].tolist()

    try:
        model = joblib.load("ai_brain.pkl")
    except:
        print("Model not found")
        return

    print("Downloading 3 years of out-of-sample data...")
    all_data = {}
    for s in symbols:
        try:
            df = yf.download(s, period="3y", progress=False)
            if len(df) > 100:
                all_data[s] = df
        except:
            pass
            
    print(f"Testing thresholds on {len(all_data)} stocks...")
    
    thresholds = [0.60, 0.65, 0.70]
    results = {t: {'trades': 0, 'wins': 0, 'losses': 0} for t in thresholds}

    for s, df in all_data.items():
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df['Vol_ZScore'] = (df['Volume'] - df['Volume'].rolling(window=20).mean()) / df['Volume'].rolling(window=20).std()
        df['Gap_Pct'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)
        df['TR'] = pd.concat([
            df['High'] - df['Low'],
            (df['High'] - df['Close'].shift(1)).abs(),
            (df['Low'] - df['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        df['ATR_14'] = df['TR'].rolling(window=14).mean()
        df['ATR_Pct'] = df['ATR_14'] / df['Close']
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
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
        
        df_clean = df.dropna().copy()
        if len(df_clean) == 0: continue
        
        features = df_clean[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret', 'MACD_Hist', 'Dist_BBLower']]
        probs = model.predict_proba(features)[:, 1]
        df_clean['AI_Prob'] = probs
        
        for t in thresholds:
            buy_signals = df_clean[df_clean['AI_Prob'] > t]
            for idx in buy_signals.index:
                i = df.index.get_loc(idx)
                if i >= len(df) - 1:
                    continue
                
                entry_price = df['Close'].iloc[i]
                target_price = entry_price * 1.07
                sl_price = entry_price * 0.97
                
                for j in range(1, 16):
                    if i + j >= len(df):
                        break
                    
                    future_high = df['High'].iloc[i + j]
                    future_low = df['Low'].iloc[i + j]
                    
                    if future_low <= sl_price:
                        results[t]['losses'] += 1
                        results[t]['trades'] += 1
                        break
                    if future_high >= target_price:
                        results[t]['wins'] += 1
                        results[t]['trades'] += 1
                        break

    print("\n--- RESULTS ---")
    for t in thresholds:
        r = results[t]
        win_rate = (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0
        print(f"Threshold: > {int(t*100)}%")
        print(f"Total Trades: {r['trades']}")
        print(f"Win Rate: {win_rate:.2f}%")
        print("-" * 20)

test_thresholds()

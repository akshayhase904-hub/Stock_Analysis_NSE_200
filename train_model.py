import pandas as pd
import yfinance as yf
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score

def compute_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

def build_features_and_target(symbols):
    print(f"Downloading historical data for {len(symbols)} stocks (7 Years of History)...")
    # Fetch 7 years of data to cover multiple market cycles (bull, bear, sideways)
    data = yf.download(symbols, period="7y", group_by="ticker", threads=True, progress=True)
    
    features = []
    
    for symbol in symbols:
        try:
            df = data[symbol].copy()
            
            df.dropna(inplace=True)
            if len(df) < 50: 
                continue
                
            # 1. Volume Z-Score
            vol_mean = df['Volume'].rolling(window=20).mean()
            vol_std = df['Volume'].rolling(window=20).std()
            df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
            
            # 2. Gap %
            df['Gap_Pct'] = (df['Open'] - df['High'].shift(1)) / df['High'].shift(1)
            
            # 3. ATR %
            df['ATR'] = compute_atr(df, 14)
            df['ATR_Pct'] = df['ATR'] / df['Close']
            
            # 4. RSI
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI_14'] = 100 - (100 / (1 + rs))
            
            # 5. EMA distances
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['Dist_EMA20'] = (df['Close'] - df['EMA_20']) / df['EMA_20']
            df['Dist_EMA50'] = (df['Close'] - df['EMA_50']) / df['EMA_50']
            
            # 6. Daily Return
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
            
            # Generate Target (Y)
            # Did it hit +7% before -3% within 15 days?
            target_list = [0] * len(df)
            
            for i in range(50, len(df) - 15):
                entry_price = df['Close'].iloc[i]
                target_price = entry_price * 1.07
                sl_price = entry_price * 0.97
                
                hit_target = False
                for j in range(1, 16):
                    future_high = df['High'].iloc[i + j]
                    future_low = df['Low'].iloc[i + j]
                    
                    if future_low <= sl_price:
                        # Hit SL first
                        break
                    if future_high >= target_price:
                        # Hit target!
                        hit_target = True
                        break
                
                if hit_target:
                    target_list[i] = 1
                    
            df['Target_Met'] = target_list
                    
            # Drop NaN rows due to rolling windows and future looking
            df_clean = df.iloc[50:-15].copy()
            df_clean.dropna(inplace=True)
            
            for idx, row in df_clean.iterrows():
                features.append({
                    'Vol_ZScore': row['Vol_ZScore'],
                    'Gap_Pct': row['Gap_Pct'],
                    'ATR_Pct': row['ATR_Pct'],
                    'RSI_14': row['RSI_14'],
                    'Dist_EMA20': row['Dist_EMA20'],
                    'Dist_EMA50': row['Dist_EMA50'],
                    'Daily_Ret': row['Daily_Ret'],
                    'MACD_Hist': row['MACD_Hist'],
                    'Dist_BBLower': row['Dist_BBLower'],
                    'Target': int(row['Target_Met'])
                })
        except Exception as e:
            pass

    return pd.DataFrame(features)

def train():
    df_symbols = pd.read_csv("nifty200_symbols.csv")
    symbols = df_symbols["Yahoo_Symbol"].tolist()
    
    print("Building Dataset...")
    df = build_features_and_target(symbols)
    
    if len(df) == 0:
        print("Error: No data available for training.")
        return
        
    print(f"Dataset Built! Total samples: {len(df)}")
    print(f"Total Winning Setups: {df['Target'].sum()} ({(df['Target'].sum()/len(df))*100:.2f}%)")
    
    X = df[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret', 'MACD_Hist', 'Dist_BBLower']]
    y = df['Target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Quantum Machine Learning Model (Random Forest)...")
    # Tuned hyperparameters to increase accuracy
    model = RandomForestClassifier(n_estimators=300, max_depth=15, min_samples_split=10, class_weight='balanced', random_state=42)
    model.fit(X_train, y_train)
    
    # Test
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # We want to force a HIGH win rate (precision).
    # So we don't just use predict(). We use probability > 0.65
    high_conf_preds = (y_prob > 0.65).astype(int)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, high_conf_preds, zero_division=0)
    
    print(f"Base Accuracy: {acc*100:.2f}%")
    print(f"High-Confidence Precision (Win Rate of AI picks): {prec*100:.2f}%")
    
    print("Saving AI Model to 'ai_brain.pkl.gz'...")
    import gzip
    with gzip.open("ai_brain.pkl.gz", "wb") as f:
        pickle.dump(model, f)
        
    try:
        import file_manager
        file_manager.split_file("ai_brain.pkl.gz", chunk_size_mb=20)
    except Exception as e:
        print(f"File splitting failed: {e}")
        
    print("Done!")

if __name__ == "__main__":
    train()

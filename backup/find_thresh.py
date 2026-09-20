import pickle
import pandas as pd
from train_model import build_features_and_target
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score

def find_threshold():
    print("Loading Dataset...")
    df_symbols = pd.read_csv("nifty200_symbols.csv")
    symbols = df_symbols["Yahoo_Symbol"].tolist()
    
    df = build_features_and_target(symbols)
    
    X = df[['Vol_ZScore', 'Gap_Pct', 'ATR_Pct', 'RSI_14', 'Dist_EMA20', 'Dist_EMA50', 'Daily_Ret']]
    y = df['Target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    with open("ai_brain.pkl", "rb") as f:
        model = pickle.load(f)
        
    y_prob = model.predict_proba(X_test)[:, 1]
    
    for thresh in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85]:
        preds = (y_prob >= thresh).astype(int)
        if sum(preds) > 0:
            prec = precision_score(y_test, preds)
            print(f"Threshold {thresh:.2f}: {prec*100:.2f}% Win Rate (Trades: {sum(preds)})")

if __name__ == "__main__":
    find_threshold()


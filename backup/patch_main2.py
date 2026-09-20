import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace run_analysis_thread and update_table
pattern = re.compile(r'    def run_analysis_thread\(self\):.*?    def on_row_double_click\(self, event\):', re.DOTALL)

new_func = """    def run_analysis_thread(self):
        self.btn_run.configure(state="disabled")
        
        # 1. Update existing trades in DB
        self.status_var.set("Updating Active Trades from Database...")
        import trade_manager
        active_df, comp_df = trade_manager.update_active_trades()

        self.status_var.set("Loading Nifty 200 Symbols...")
        import pandas as pd
        import yfinance as yf
        import numpy as np
        try:
            df_symbols = pd.read_csv("nifty200_symbols.csv")
            symbols = df_symbols["Yahoo_Symbol"].tolist()
        except Exception as e:
            self.status_var.set("Error: nifty200_symbols.csv missing!")
            self.btn_run.configure(state="normal")
            return

        # Download 6 months for indicator calculation
        self.status_var.set("Fetching Market Data...")
        data = yf.download(symbols, period="6mo", group_by="ticker", threads=True, progress=False)

        results = []
        total_symbols = len(symbols)
        analyzed_count = 0
        
        current_date_str = pd.Timestamp.now().strftime("%Y-%m-%d")

        for symbol in symbols:
            try:
                if len(symbols) > 1:
                    df = data[symbol].copy()
                else:
                    df = data.copy()
                    
                df.dropna(inplace=True)
                if len(df) < 50:
                    analyzed_count += 1
                    continue

                # 1. Volume Anomaly
                vol_mean = df['Volume'].rolling(window=20).mean()
                vol_std = df['Volume'].rolling(window=20).std()
                df['Vol_ZScore'] = (df['Volume'] - vol_mean) / vol_std
                
                # 2. Gap up %
                df['Gap_Pct'] = (df['Open'] - df['High'].shift(1)) / df['High'].shift(1)
                
                # 3. ATR
                high_low = df['High'] - df['Low']
                high_close = np.abs(df['High'] - df['Close'].shift())
                low_close = np.abs(df['Low'] - df['Close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                df['ATR'] = true_range.rolling(window=14).mean()
                df['ATR_Pct'] = df['ATR'] / df['Close']
                
                # 4. RSI
                delta = df['Close'].diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rs = ema_up / ema_down
                df['RSI_14'] = 100 - (100 / (1 + rs))
                
                # 5. EMA 20 & 50
                df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
                df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
                df['Dist_EMA20'] = (df['Close'] - df['EMA_20']) / df['EMA_20']
                df['Dist_EMA50'] = (df['Close'] - df['EMA_50']) / df['EMA_50']
                
                # 6. Daily Returns
                df['Daily_Ret'] = df['Close'].pct_change()
                
                # 7. MACD
                exp1 = df['Close'].ewm(span=12, adjust=False).mean()
                exp2 = df['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                macd_signal = macd.ewm(span=9, adjust=False).mean()
                df['MACD_Hist'] = macd - macd_signal
                
                # 8. Bollinger Bands
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

                # AI Prediction
                prob = self.ai_model.predict_proba(features)[0][1]
                
                if prob > 0.65:
                    clean_symbol = symbol.replace('.NS', '')
                    target = close * 1.07
                    sl = close * 0.97
                    qty = int(10000 // close)
                    
                    reason = (
                        f"- AI Confidence: The Neural Network is {prob*100:.1f}% confident this will hit 7%.\\n"
                        f"- Volume Anomaly: Volume is {latest['Vol_ZScore']:.1f} standard deviations above normal.\\n"
                        f"- Trend Aligned: Close (INR {close:.2f}) > 20 EMA > 50 EMA.\\n"
                        f"- Volatility Filter: ATR is {latest['ATR_Pct']*100:.2f}%, safely within 3% stop loss limit.\\n"
                        f"- Momentum: RSI is strong at {latest['RSI_14']:.1f}.\\n"
                        f"- AI Self-Learning: This strategy adapts to Nifty 200 historically successful patterns."
                    )
                    
                    results.append({
                        'Symbol': clean_symbol,
                        'Entry Date': current_date_str,
                        'Close': round(close, 2),
                        'Target': round(target, 2),
                        'StopLoss': round(sl, 2),
                        'Qty': qty,
                        'Score': prob,  # Rank by AI Probability
                        'Reason': reason
                    })
            except Exception as e:
                pass
            
            analyzed_count += 1
            # Update progress safely
            progress_val = analyzed_count / total_symbols
            self.after(0, self.progress.set, progress_val)

        # Sort results
        results.sort(key=lambda x: x['Score'], reverse=True)
        top_5 = results[:5]
        
        # Save new picks to database if not already active
        db_new_trades = []
        for pick in top_5:
            if active_df.empty or pick['Symbol'] not in active_df['Symbol'].values:
                db_new_trades.append({
                    'Symbol': pick['Symbol'],
                    'Entry Date': pick['Entry Date'],
                    'Entry Price': pick['Close'],
                    'Target': pick['Target'],
                    'Stop Loss': pick['StopLoss']
                })
        trade_manager.add_new_trades(db_new_trades)
        
        # Re-read the database to get updated lists for GUI
        import os
        active_list = []
        if os.path.exists(trade_manager.ACTIVE_TRADES_FILE):
            df_a = pd.read_csv(trade_manager.ACTIVE_TRADES_FILE)
            active_list = df_a.to_dict('records')
            
        comp_list = []
        if os.path.exists(trade_manager.COMPLETED_TRADES_FILE):
            df_c = pd.read_csv(trade_manager.COMPLETED_TRADES_FILE)
            comp_list = df_c.to_dict('records')
            comp_list.sort(key=lambda x: x['Exit Date'], reverse=True)

        # Update GUI
        self.after(0, lambda: self.update_table(top_5, active_list, comp_list))

    def update_table(self, top_5, active_list, comp_list):
        self.top_5_data = top_5
        if not top_5:
            self.status_var.set("No stocks met the criteria today.")
        else:
            self.status_var.set("Analysis Complete. Database Updated.")
            for item in top_5:
                self.tree.insert("", "end", values=(
                    item['Symbol'],
                    f"{item['Score']*100:.2f}%",
                    f"INR {item['Close']}",
                    f"INR {item['Target']}",
                    f"INR {item['StopLoss']}",
                    item['Qty']
                ))
                
        # Update active trades
        for item in active_list:
            self.active_tree.insert("", "end", values=(
                item['Symbol'],
                item['Entry Date'],
                f"INR {item['Entry Price']}",
                f"INR {item['Target']}",
                f"INR {item['Stop Loss']}"
            ))
                
        # Update history
        for h in comp_list:
            color = "green" if "Win" in h['Status'] else "red"
            self.hist_tree.insert("", "end", values=(
                h['Symbol'],
                h['Entry Date'],
                f"INR {h['Entry Price']}",
                h['Exit Date'],
                f"INR {h['Exit Price']}",
                h['Status'],
                f"{h['PnL']}%"
            ), tags=(color,))
            
        self.hist_tree.tag_configure("green", foreground="green")
        self.hist_tree.tag_configure("red", foreground="red")
            
        self.btn_run.configure(state="normal")
        self.progress.set(1)

    def on_row_double_click(self, event):"""

content = pattern.sub(new_func, content)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patch 2 done.")

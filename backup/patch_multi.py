import re

files_to_patch = ["trade_manager.py", "headless_scanner.py", "main.py"]

for filename in files_to_patch:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Replace the conditional df = ... logic with just df = data[symbol].copy()
        content = re.sub(r'if len\(yfinance_symbols\) == 1:\s*df = data\s*else:\s*df = data\[yf_sym\]', r'df = data[yf_sym].copy()', content)
        content = re.sub(r'df = data\[symbol\]\.copy\(\) if len\(symbols\) > 1 else data\.copy\(\)', r'df = data[symbol].copy()', content)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Patched {filename}")
    except Exception as e:
        print(f"Failed {filename}: {e}")

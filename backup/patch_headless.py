import re

with open("headless_scanner.py", "rb") as f:
    content = f.read().decode("latin1")
    
content = re.sub(r'df = data\[symbol\]\.copy\(\) if len\(symbols\) > 1 else data\.copy\(\)', r'df = data[symbol].copy()', content)

with open("headless_scanner.py", "wb") as f:
    f.write(content.encode("utf-8"))
    
print("Patched headless_scanner.py")

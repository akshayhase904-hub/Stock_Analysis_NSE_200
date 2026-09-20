import re

with open("train_model.py", "rb") as f:
    content = f.read().decode("latin1")
    
content = re.sub(r'if len\(symbols\) > 1:\s*df = data\[symbol\]\.copy\(\)\s*else:\s*df = data\.copy\(\)', r'df = data[symbol].copy()', content)

with open("train_model.py", "wb") as f:
    f.write(content.encode("utf-8"))
    
print("Patched train_model.py")

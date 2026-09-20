with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("        import trade_manager\n", "            import trade_manager\n")

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

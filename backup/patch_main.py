import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
if "import trade_manager" not in content:
    content = content.replace("import pickle\n", "import pickle\nimport trade_manager\n")

# 2. Add Live Active Trades tab
tab_str = """        self.tab_today = self.tabview.add("Today's Picks")
        self.tab_active = self.tabview.add("Live Active Trades")
        self.tab_hist = self.tabview.add("Last 3 Months Trades")"""
content = re.sub(r'        self\.tab_today = self\.tabview\.add\("Today\'s Picks"\)\n        self\.tab_hist = self\.tabview\.add\("Last 3 Months Trades"\)', tab_str, content)

# 3. Add active_tree
tree_str = """        # Today's Picks Treeview
        columns = ("Symbol", "Probability", "Close", "Target (+7%)", "Stop Loss (-3%)", "Qty (10k INR)")
        self.tree = ttk.Treeview(self.tab_today, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # Active Trades Treeview
        active_cols = ("Symbol", "Entry Date", "Entry Price", "Target", "Stop Loss")
        self.active_tree = ttk.Treeview(self.tab_active, columns=active_cols, show="headings")
        for col in active_cols:
            self.active_tree.heading(col, text=col)
            self.active_tree.column(col, width=130, anchor="center")
        self.active_tree.pack(fill="both", expand=True)"""
content = re.sub(r'        # Treeview.*?self\.tree\.bind\("<Double-1>", self\.on_row_double_click\)', tree_str, content, flags=re.DOTALL)

# 4. Clear trees in start_analysis
clear_str = """        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.active_tree.get_children():
            self.active_tree.delete(item)
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)"""
content = re.sub(r'        for item in self\.tree\.get_children\(\):\n            self\.tree\.delete\(item\)\n        for item in self\.hist_tree\.get_children\(\):\n            self\.hist_tree\.delete\(item\)', clear_str, content)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patch 1 done.")

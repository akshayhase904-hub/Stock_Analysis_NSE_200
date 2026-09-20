with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_str = """        self.tab_today = self.tabview.add("Today's Picks")
        self.tab_history = self.tabview.add("Last 3 Months Trades")"""

new_str = """        self.tab_today = self.tabview.add("Today's Picks")
        self.tab_active = self.tabview.add("Live Active Trades")
        self.tab_hist = self.tabview.add("Last 3 Months Trades")"""

content = content.replace(old_str, new_str)
# Wait, also we need to change self.tab_history in the hist treeview to self.tab_hist
old_tree_str = "self.hist_tree = ttk.Treeview(self.tab_history"
new_tree_str = "self.hist_tree = ttk.Treeview(self.tab_hist"
content = content.replace(old_tree_str, new_tree_str)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

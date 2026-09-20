import pandas as pd
import os

def generate_html():
    active_html = ""
    comp_html = ""
    
    if os.path.exists("active_trades.csv"):
        active_df = pd.read_csv("active_trades.csv")
        active_html = active_df.to_html(classes='table table-striped table-hover', index=False)
        
    if os.path.exists("completed_trades.csv"):
        comp_df = pd.read_csv("completed_trades.csv")
        # Color code the rows based on status
        def row_color(val):
            if not isinstance(val, str):
                return ''
            if 'Win' in val:
                return 'background-color: #d4edda;'
            if 'Loss' in val:
                return 'background-color: #f8d7da;'
            return ''

        comp_html = (
            comp_df.style
            .map(lambda x: row_color(x) if isinstance(x, str) and ('Win' in x or 'Loss' in x) else '', subset=['Status'])
            .to_html(classes='table table-striped table-hover', index=False)
        )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Trading Portfolio</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="container mt-5">
        <h1 class="mb-4">?? AI Trading Portfolio</h1>
        
        <h3>Live Active Trades</h3>
        <div class="table-responsive mb-5">
            {active_html if active_html else "<p>No active trades right now.</p>"}
        </div>
        
        <h3>Completed Trades Ledger</h3>
        <div class="table-responsive">
            {comp_html if comp_html else "<p>No completed trades yet.</p>"}
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_html()

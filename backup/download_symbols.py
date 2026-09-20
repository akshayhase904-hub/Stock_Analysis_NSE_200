import pandas as pd
import urllib.request
import io

def download_nifty200():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        csv_data = response.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_data))
        # Symbols need to have .NS for yfinance
        df['Yahoo_Symbol'] = df['Symbol'] + ".NS"
        df[['Company Name', 'Industry', 'Symbol', 'Yahoo_Symbol']].to_csv('nifty200_symbols.csv', index=False)
        print("Successfully downloaded and saved Nifty 200 symbols.")
    except Exception as e:
        print(f"Failed to download Nifty 200 list: {e}")

if __name__ == "__main__":
    download_nifty200()


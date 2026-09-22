# dividend_fetcher.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
from database import DatabaseManager

STOCKS = {
    
    "SCOM": "https://stockanalysis.com/quote/nase/SCOM/dividend/",
    "EQTY": "https://stockanalysis.com/quote/nase/EQTY/dividend/",
    "KPLC": "https://stockanalysis.com/quote/nase/KPLC/dividend/",
    "KEGN": "https://stockanalysis.com/quote/nase/KEGN/dividend/",
    "BAT":  "https://stockanalysis.com/quote/nase/BAT/dividend/",
    "SCBK": "https://stockanalysis.com/quote/nase/SCBK/dividend/",
    "SBIC": "https://stockanalysis.com/quote/nase/SBIC/dividend/",
    "KAPC": "https://stockanalysis.com/quote/nase/KAPC/dividend/",
}


def fetch_dividend_history(ticker, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if not table:
        return None
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) >= 2:
            ex_date = cells[0].get_text(strip=True)
            amount = cells[1].get_text(strip=True)
            amount_clean = amount.replace("KES", "").replace(",", "").strip()
            try:
                rows.append({
                    "ticker": ticker,
                    "ex_date": ex_date,
                    "amount_per_share": float(amount_clean),
                })
            except ValueError:
                continue
    return pd.DataFrame(rows)

def update_dividend_database():
    db = DatabaseManager()
    for ticker, url in STOCKS.items():
        print(f"Fetching {ticker}...")
        df = fetch_dividend_history(ticker, url)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                db.client.table("nse_dividends").upsert({
                    "ticker": ticker,
                    "ex_date": row["ex_date"],
                    "amount_per_share": row["amount_per_share"],
                }, on_conflict="ticker,ex_date").execute()
            print(f"  Updated {len(df)} dividends")
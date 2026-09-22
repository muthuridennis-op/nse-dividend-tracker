# dividend_fetcher.py
"""Scrapes NSE dividend history from StockAnalysis.com into Supabase."""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from config import STOCKS, EX_DIVIDEND_ALERT_DAYS
from database import DatabaseManager, _send_telegram
from logger import get_logger

log = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_dividend_history(ticker: str, url: str) -> list:
    """Return list of dicts with ticker, ex_date, amount_per_share."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning("%s fetch failed: %s", ticker, e)
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    table = soup.find("table")
    if not table:
        log.warning("%s: no table found", ticker)
        return []

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue
        date_text = cells[0].get_text(strip=True)
        amount_text = cells[1].get_text(strip=True)
        amount_clean = amount_text.replace("KES", "").replace(",", "").strip()
        try:
            amount = float(amount_clean)
        except ValueError:
            continue

        # Try to parse date
        parsed_date = None
        for fmt in ("%b %d, %Y", "%Y-%m-%d", "%d %b %Y", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(date_text, fmt).date()
                break
            except ValueError:
                continue
        if not parsed_date:
            continue

        rows.append({
            "ticker": ticker,
            "ex_date": parsed_date.isoformat(),
            "amount_per_share": amount,
        })

    return rows


def check_upcoming_dividends(db, days_ahead: int):
    """Alert via Telegram about ex-dates coming up."""
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    try:
        resp = db.client.table("nse_dividends") \
            .select("*") \
            .gte("ex_date", today.isoformat()) \
            .lte("ex_date", cutoff.isoformat()) \
            .order("ex_date") \
            .execute()
    except Exception as e:
        log.warning("Upcoming dividend query failed: %s", e)
        return

    for div in resp.data:
        msg = (
            f"📅 *{div['ticker']}* ex-dividend: {div['ex_date']}\n"
            f"Amount: {div['amount_per_share']} KES per share\n"
            f"Buy before this date to receive this payout."
        )
        _send_telegram(msg)


def main():
    log.info("Starting NSE dividend fetch...")
    db = DatabaseManager()

    total = 0
    for ticker, url in STOCKS.items():
        log.info("Fetching %s", ticker)
        rows = fetch_dividend_history(ticker, url)
        if rows:
            count = db.upsert_dividends(rows)
            total += count
            log.info("  %s: %d rows upserted", ticker, count)
        else:
            log.warning("  %s: no rows", ticker)

    log.info("Total upserted: %d", total)

    # Send alerts for upcoming ex-dates
    check_upcoming_dividends(db, EX_DIVIDEND_ALERT_DAYS)

    log.info("Done.")


if __name__ == "__main__":
    main()
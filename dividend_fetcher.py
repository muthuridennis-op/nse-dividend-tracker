# dividend_fetcher.py
"""Scrapes NSE dividend history from StockAnalysis.com and Fiscal.ai into Supabase."""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from config import STOCKS, EX_DIVIDEND_ALERT_DAYS
from database import DatabaseManager, _send_telegram
from logger import get_logger

log = get_logger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Fiscal.ai uses different URL slugs for some tickers.
# Map your tickers to their Fiscal.ai equivalents.
FISCAL_MAP = {
    "NSE":  "NASE-NSE",
    "SCOM": "NASE-SCOM",
    "EQTY": "NASE-EQTY",
    "BAT":  "NASE-BAT",
    "TOTL": "NASE-TOTL",
    "KCB":  "NASE-KCB",
    # Add more as you expand your stock list.
}


def fetch_from_stockanalysis(ticker: str, url: str) -> list:
    """Existing StockAnalysis.com scraper."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning("%s (StockAnalysis) fetch failed: %s", ticker, e)
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    table = soup.find("table")
    if not table:
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
            "source": "stockanalysis",
        })
    return rows


def fetch_from_fiscal(ticker: str) -> list:
    """Scrape dividend history from Fiscal.ai."""
    slug = FISCAL_MAP.get(ticker)
    if not slug:
        return []

    url = f"https://fiscal.ai/company/{slug}/dividends/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning("%s (Fiscal.ai) fetch failed: %s", ticker, e)
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        # Fiscal.ai columns: Ex Date | Pay Date | Type | Amount
        ex_date_text = cells[0].get_text(strip=True)
        amount_text = cells[3].get_text(strip=True) if len(cells) > 3 else cells[2].get_text(strip=True)

        amount_clean = amount_text.replace("KES", "").replace(",", "").strip()
        try:
            amount = float(amount_clean)
        except ValueError:
            continue

        parsed_date = None
        for fmt in ("%b %d, %Y", "%Y-%m-%d", "%d %b %Y"):
            try:
                parsed_date = datetime.strptime(ex_date_text, fmt).date()
                break
            except ValueError:
                continue
        if not parsed_date:
            continue

        rows.append({
            "ticker": ticker,
            "ex_date": parsed_date.isoformat(),
            "amount_per_share": amount,
            "source": "fiscal",
        })
    return rows


def merge_sources(*source_lists):
    """Merge rows from multiple sources, deduplicating by (ticker, ex_date)."""
    merged = {}
    for rows in source_lists:
        for row in rows:
            key = (row["ticker"], row["ex_date"])
            # Prefer the row with a source field if not already present
            if key not in merged:
                merged[key] = row
            else:
                # If both have the same date, keep the one with the larger amount
                # (usually the "Multiple Dividends" total from Fiscal.ai)
                if row["amount_per_share"] > merged[key]["amount_per_share"]:
                    merged[key] = row
    return list(merged.values())


def check_upcoming_dividends(db, days_ahead: int):
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

        sa_rows = fetch_from_stockanalysis(ticker, url)
        fiscal_rows = fetch_from_fiscal(ticker)

        merged = merge_sources(sa_rows, fiscal_rows)
        if merged:
            count = db.upsert_dividends(merged)
            total += count
            log.info("  %s: %d rows (SA=%d, Fiscal=%d, merged=%d)",
                     ticker, count, len(sa_rows), len(fiscal_rows), len(merged))
        else:
            log.warning("  %s: no rows from any source", ticker)

    log.info("Total upserted: %d", total)
    check_upcoming_dividends(db, EX_DIVIDEND_ALERT_DAYS)
    log.info("Done.")


if __name__ == "__main__":
    main()
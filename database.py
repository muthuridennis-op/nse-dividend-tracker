# database.py
"""Supabase client + Telegram notifications."""
import os
import sys
import httpx
from supabase import create_client
from logger import get_logger

log = get_logger(__name__)


def _send_telegram(message: str):
    """Fire-and-forget Telegram notification. Never raises."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return

    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        log.info("Telegram sent")
    except Exception as e:
        log.warning("Telegram failed: %s", e)


class DatabaseManager:
    def __init__(self):
        # Sanitize credentials: strip whitespace and stray quotes
        url = os.environ.get("SUPABASE_URL", "").strip().strip('"').strip("'")
        key = (
            os.environ.get("SUPABASE_SERVICE_KEY")
            or os.environ.get("SUPABASE_KEY")
            or ""
        ).strip().strip('"').strip("'")

        # Remove any trailing slash — Supabase client rejects it
        url = url.rstrip("/")

        # Validate before handing to create_client
        if not url or not key:
            log.critical("Supabase credentials missing.")
            log.critical("URL length: %d, Key length: %d", len(url), len(key))
            sys.exit(1)

        if not url.startswith("https://"):
            log.critical("Invalid Supabase URL: %s", url)
            log.critical("Expected format: https://xxxx.supabase.co")
            sys.exit(1)

        if "supabase.co" not in url:
            log.critical("URL does not contain supabase.co: %s", url)
            sys.exit(1)

        try:
            self.client = create_client(url, key)
            log.info("Supabase client initialized.")
        except Exception as e:
            log.critical("Supabase client init failed: %s", e)
            sys.exit(1)

    def upsert_dividends(self, rows):
        """Upsert dividend rows. Returns count of successful upserts."""
        inserted = 0
        for row in rows:
            try:
                self.client.table("nse_dividends").upsert(
                    row, on_conflict="ticker,ex_date"
                ).execute()
                inserted += 1
            except Exception as e:
                log.warning("Upsert failed for %s: %s", row.get("ticker"), e)
        return inserted
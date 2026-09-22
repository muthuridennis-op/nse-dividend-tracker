# dividend_calendar.py
from datetime import datetime, timedelta
from database import DatabaseManager

def check_upcoming_dividends(days_ahead=14):
    db = DatabaseManager()
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    response = db.client.table("nse_dividends") \
        .select("*") \
        .gte("ex_date", today.isoformat()) \
        .lte("ex_date", cutoff.isoformat()) \
        .order("ex_date") \
        .execute()

    for div in response.data:
        message = (
            f"📅 *{div['ticker']}* ex-date: {div['ex_date']}\n"
            f"Dividend: {div['amount_per_share']} KES per share\n"
            f"Buy before this date to receive this payout."
        )
        send_telegram(message)
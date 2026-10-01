# NSE Dividend Tracker

A dividend tracking dashboard for the Nairobi Securities Exchange.

- **Backend**: Supabase (holdings, dividends, income)
- **Frontend**: Streamlit
- **Keep-alive**: GitHub Actions pings the app every 6 hours

## Deployment

Deployed on Streamlit Community Cloud.

## Files

- `dashboard_nse.py` — Streamlit dashboard
- `dividend_fetcher.py` — Scrapes dividend data
- `dividend_calendar.py` — Ex-dividend alerts
- `database.py` — Supabase client + Telegram
- `config.py` — Stock URLs and metadata
- `logger.py` — Logging setup
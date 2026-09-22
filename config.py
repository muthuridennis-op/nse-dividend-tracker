# config.py
"""NSE Dividend Tracker configuration."""

# The 8 stocks you follow
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

# Company metadata for display
COMPANIES = {
    "SCOM": {"name": "Safaricom",        "sector": "Telecom"},
    "EQTY": {"name": "Equity Group",     "sector": "Banking"},
    "KPLC": {"name": "Kenya Power",      "sector": "Utilities"},
    "KEGN": {"name": "KenGen",           "sector": "Energy"},
    "BAT":  {"name": "BAT Kenya",        "sector": "Consumer"},
    "SCBK": {"name": "StanChart Kenya",  "sector": "Banking"},
    "SBIC": {"name": "Stanbic Holdings", "sector": "Banking"},
    "KAPC": {"name": "Kapchorua Tea",    "sector": "Agriculture"},
}

# Withholding tax on NSE dividends (Kenyan residents)
WITHHOLDING_TAX_PCT = 5.0

# Telegram
TELEGRAM_ENABLED = True

# How many days ahead to alert about ex-dividend dates
EX_DIVIDEND_ALERT_DAYS = 14
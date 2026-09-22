# dashboard_nse.py
"""
NSE Dividend Tracker — Streamlit dashboard.

Reads holdings, dividend history, and income received from Supabase.
Calculates yield-on-cost, forward income, and ex-dividend countdowns.
Frontend uses the anon key (RLS-protected, read-only).
"""
import os
from datetime import datetime, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="NSE Dividend Tracker",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# Supabase connection (Option A: direct client)
# ------------------------------------------------------------------
@st.cache_resource
def init_supabase():
    # Prefer st.secrets (Streamlit Cloud); fall back to env (local dev)
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        url = None
        key = None

    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        st.error("🚨 Supabase credentials missing. Check st.secrets or .env")
        st.stop()

    return create_client(url, key)


supabase = init_supabase()

# ------------------------------------------------------------------
# Static company metadata (for display, no scraping needed)
# ------------------------------------------------------------------
COMPANIES = {
    "SCOM": {"name": "Safaricom",          "sector": "Telecom"},
    "EQTY": {"name": "Equity Group",       "sector": "Banking"},
    "KPLC": {"name": "Kenya Power",        "sector": "Utilities"},
    "KEGN": {"name": "KenGen",             "sector": "Energy"},
    "BAT":  {"name": "BAT Kenya",          "sector": "Consumer"},
    "SCBK": {"name": "StanChart Kenya",    "sector": "Banking"},
    "SBIC": {"name": "Stanbic Holdings",   "sector": "Banking"},
    "KAPC": {"name": "Kapchorua Tea",      "sector": "Agriculture"},
}

# Withholding tax rate on NSE dividends (Kenyan resident)
WITHHOLDING_TAX_PCT = 5.0


# ------------------------------------------------------------------
# Data fetch helpers
# ------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_holdings():
    resp = supabase.table("nse_holdings").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_dividends():
    resp = (
        supabase.table("nse_dividends")
        .select("*")
        .order("ex_date", desc=True)
        .execute()
    )
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_income():
    resp = (
        supabase.table("nse_income_received")
        .select("*")
        .order("payment_date", desc=True)
        .execute()
    )
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


def trailing_12m_dividend(ticker, dividends_df):
    """Sum of all dividends with ex_date in the last 365 days."""
    if dividends_df.empty or "ex_date" not in dividends_df.columns:
        return 0.0
    df = dividends_df[dividends_df["ticker"] == ticker].copy()
    if df.empty:
        return 0.0
    df["ex_date"] = pd.to_datetime(df["ex_date"], errors="coerce")
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
    recent = df[df["ex_date"] >= cutoff]
    return float(recent["amount_per_share"].sum())


# ------------------------------------------------------------------
# Sidebar — add holdings and record income
# ------------------------------------------------------------------
with st.sidebar:
    st.header("📥 Add a Holding")

    with st.form("add_holding", clear_on_submit=True):
        ticker = st.selectbox(
            "Ticker",
            list(COMPANIES.keys()),
            format_func=lambda t: f"{t} — {COMPANIES[t]['name']}",
        )
        shares = st.number_input("Shares owned", min_value=0.0, step=1.0)
        avg_price = st.number_input("Average buy price (KES)", min_value=0.0, step=0.5)
        acquired = st.date_input("Date acquired", value=date.today())

        submitted = st.form_submit_button("Add holding", use_container_width=True)
        if submitted and shares > 0:
            try:
                supabase.table("nse_holdings").insert({
                    "ticker": ticker,
                    "company_name": COMPANIES[ticker]["name"],
                    "shares_owned": float(shares),
                    "average_buy_price": float(avg_price),
                    "date_acquired": acquired.isoformat(),
                }).execute()
                st.success(f"Added {shares} shares of {ticker}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Insert failed: {e}")

    st.divider()
    st.header("💰 Record Dividend Income")

    with st.form("add_income", clear_on_submit=True):
        inc_ticker = st.selectbox("Ticker", list(COMPANIES.keys()), key="inc_ticker")
        amount = st.number_input("Amount received (KES)", min_value=0.0, step=10.0)
        paid_on = st.date_input("Payment date", value=date.today())

        submitted_inc = st.form_submit_button("Record income", use_container_width=True)
        if submitted_inc and amount > 0:
            try:
                supabase.table("nse_income_received").insert({
                    "ticker": inc_ticker,
                    "payment_date": paid_on.isoformat(),
                    "amount_received": float(amount),
                    "shares_held_at_payment": 0,
                    "withholding_tax": float(amount) * WITHHOLDING_TAX_PCT / 100.0,
                }).execute()
                st.success(f"Recorded {amount} KES from {inc_ticker}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Insert failed: {e}")

    st.divider()
    st.caption(f"Withholding tax applied: {WITHHOLDING_TAX_PCT}%")
    st.caption("Data refreshes every 5 minutes.")


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("🇰🇪 NSE Dividend Tracker")
st.caption("Buy-and-hold dividend portfolio • Kenyan stock exchange")

holdings_df = fetch_holdings()
dividends_df = fetch_dividends()
income_df = fetch_income()


# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab_holdings, tab_calendar, tab_income = st.tabs(
    ["📊 My Holdings", "📅 Ex-Dividend Calendar", "💰 Income Received"]
)


# =========================================================
# TAB 1 — Holdings & Yield on Cost
# =========================================================
with tab_holdings:
    if holdings_df.empty:
        st.info("No holdings yet. Use the sidebar to add your first position.")
    else:
        df = holdings_df.copy()
        df["company_name"] = df["ticker"].map(
            lambda t: COMPANIES.get(t, {}).get("name", t)
        )

        # Compute trailing 12-month dividend and derived metrics
        df["t12m_div_per_share"] = df["ticker"].apply(
            lambda t: trailing_12m_dividend(t, dividends_df)
        )
        df["annual_income"] = df["shares_owned"] * df["t12m_div_per_share"]
        df["yield_on_cost"] = df.apply(
            lambda r: (r["t12m_div_per_share"] / r["average_buy_price"] * 100)
            if r["average_buy_price"] > 0 else 0.0,
            axis=1,
        )
        df["position_value"] = df["shares_owned"] * df["average_buy_price"]

        total_income = df["annual_income"].sum()
        total_invested = df["position_value"].sum()
        portfolio_yoc = (total_income / total_invested * 100) if total_invested > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested (KES)", f"{total_invested:,.0f}")
        col2.metric("Trailing 12m Income (KES)", f"{total_income:,.0f}")
        col3.metric("Portfolio Yield on Cost", f"{portfolio_yoc:.2f}%")

        st.divider()

        # Formatted display table
        display = df[[
            "ticker", "company_name", "shares_owned",
            "average_buy_price", "t12m_div_per_share",
            "yield_on_cost", "annual_income",
        ]].copy()
        display.columns = [
            "Ticker", "Company", "Shares",
            "Avg Price (KES)", "T12m Div/Share (KES)",
            "Yield on Cost (%)", "Annual Income (KES)",
        ]
        display["Avg Price (KES)"] = display["Avg Price (KES)"].round(2)
        display["T12m Div/Share (KES)"] = display["T12m Div/Share (KES)"].round(2)
        display["Yield on Cost (%)"] = display["Yield on Cost (%)"].round(2)
        display["Annual Income (KES)"] = display["Annual Income (KES)"].round(0)

        st.dataframe(display, use_container_width=True, hide_index=True)

        # Bar chart of annual income by ticker
        st.markdown("### Annual Income by Company")
        chart_df = df[["ticker", "annual_income"]].sort_values("annual_income", ascending=True)
        fig = go.Figure(go.Bar(
            x=chart_df["annual_income"],
            y=chart_df["ticker"],
            orientation="h",
            marker_color="#2ca02c",
            text=[f"{v:,.0f} KES" for v in chart_df["annual_income"]],
            textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark",
            height=max(220, 40 * len(chart_df)),
            margin=dict(l=10, r=60, t=10, b=10),
            xaxis_title="Annual Income (KES)",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)


# =========================================================
# TAB 2 — Ex-Dividend Calendar
# =========================================================
with tab_calendar:
    st.subheader("Upcoming Ex-Dividend Dates")

    if dividends_df.empty:
        st.info("No dividend data yet. Run the fetcher workflow first.")
    else:
        div = dividends_df.copy()
        div["ex_date"] = pd.to_datetime(div["ex_date"], errors="coerce")
        today = pd.Timestamp.today().normalize()

        upcoming = div[div["ex_date"] >= today].sort_values("ex_date").head(20)
        past = div[div["ex_date"] < today].sort_values("ex_date", ascending=False).head(20)

        if not upcoming.empty:
            upcoming["days_until"] = (upcoming["ex_date"] - today).dt.days
            display_up = upcoming[["ticker", "ex_date", "amount_per_share", "days_until"]].copy()
            display_up.columns = ["Ticker", "Ex-Date", "Dividend (KES)", "Days Until"]
            display_up["Ex-Date"] = display_up["Ex-Date"].dt.strftime("%Y-%m-%d")
            display_up["Dividend (KES)"] = display_up["Dividend (KES)"].round(2)
            st.dataframe(display_up, use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming ex-dividend dates on record.")

        st.divider()
        st.subheader("Recent Dividend History")
        if not past.empty:
            display_past = past[["ticker", "ex_date", "amount_per_share"]].copy()
            display_past.columns = ["Ticker", "Ex-Date", "Dividend (KES)"]
            display_past["Ex-Date"] = display_past["Ex-Date"].dt.strftime("%Y-%m-%d")
            display_past["Dividend (KES)"] = display_past["Dividend (KES)"].round(2)
            st.dataframe(display_past, use_container_width=True, hide_index=True)


# =========================================================
# TAB 3 — Income Received
# =========================================================
with tab_income:
    st.subheader("Dividend Income Log")

    if income_df.empty:
        st.info("No dividends recorded yet. Use the sidebar to log them as they arrive.")
    else:
        inc = income_df.copy()
        inc["payment_date"] = pd.to_datetime(inc["payment_date"], errors="coerce")
        inc = inc.dropna(subset=["payment_date"]).sort_values("payment_date")

        total_received = inc["amount_received"].sum()
        total_tax = inc["withholding_tax"].fillna(0).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Received (KES)", f"{total_received:,.2f}")
        col2.metric("Withholding Tax (KES)", f"{total_tax:,.2f}")
        col3.metric("Net Income (KES)", f"{total_received - total_tax:,.2f}")

        st.divider()

        # Cumulative income line chart
        inc["cumulative"] = inc["amount_received"].cumsum()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=inc["payment_date"],
            y=inc["cumulative"],
            mode="lines+markers",
            line=dict(color="#2ca02c", width=2),
            name="Cumulative Income",
        ))
        fig.update_layout(
            template="plotly_dark",
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Date",
            yaxis_title="Cumulative Income (KES)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Raw table
        display_inc = inc[["ticker", "payment_date", "amount_received", "withholding_tax"]].copy()
        display_inc.columns = ["Ticker", "Payment Date", "Amount (KES)", "Tax (KES)"]
        display_inc["Payment Date"] = display_inc["Payment Date"].dt.strftime("%Y-%m-%d")
        display_inc["Amount (KES)"] = display_inc["Amount (KES)"].round(2)
        display_inc["Tax (KES)"] = display_inc["Tax (KES)"].fillna(0).round(2)
        st.dataframe(display_inc, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------
st.divider()
st.caption(
    "NSE Dividend Tracker • Data refreshes every 5 minutes • "
    "Not investment advice"
)
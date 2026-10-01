# pages/1_Holdings.py
import os
from datetime import date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

COMPANIES = {
    "SCOM": {"name": "Safaricom", "sector": "Telecom"},
    "EQTY": {"name": "Equity Group", "sector": "Banking"},
    "KPLC": {"name": "Kenya Power", "sector": "Utilities"},
    "KEGN": {"name": "KenGen", "sector": "Energy"},
    "BAT":  {"name": "BAT Kenya", "sector": "Consumer"},
    "SCBK": {"name": "StanChart Kenya", "sector": "Banking"},
    "SBIC": {"name": "Stanbic Holdings", "sector": "Banking"},
    "KAPC": {"name": "Kapchorua Tea", "sector": "Agriculture"},
}
WITHHOLDING_TAX_PCT = 5.0


@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        url, key = None, None
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase credentials missing.")
        st.stop()
    return create_client(url, key)


supabase = init_supabase()


@st.cache_data(ttl=300)
def fetch_holdings():
    resp = supabase.table("nse_holdings").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_dividends():
    resp = supabase.table("nse_dividends").select("*").order("ex_date", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


def trailing_12m_dividend(ticker, dividends_df):
    if dividends_df.empty:
        return 0.0
    df = dividends_df[dividends_df["ticker"] == ticker].copy()
    if df.empty:
        return 0.0
    df["ex_date"] = pd.to_datetime(df["ex_date"], errors="coerce")
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
    return float(df[df["ex_date"] >= cutoff]["amount_per_share"].sum())


with st.sidebar:
    st.header("📥 Add a Holding")
    with st.form("add_holding", clear_on_submit=True):
        ticker = st.selectbox("Ticker", list(COMPANIES.keys()),
                              format_func=lambda t: f"{t} — {COMPANIES[t]['name']}")
        shares = st.number_input("Shares owned", min_value=0.0, step=1.0)
        avg_price = st.number_input("Average buy price (KES)", min_value=0.0, step=0.5)
        acquired = st.date_input("Date acquired", value=date.today())
        if st.form_submit_button("Add holding", use_container_width=True) and shares > 0:
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
        if st.form_submit_button("Record income", use_container_width=True) and amount > 0:
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


st.title("🇰🇪 My Holdings")
st.caption("Buy-and-hold dividend portfolio • Kenyan stock exchange")

holdings_df = fetch_holdings()
dividends_df = fetch_dividends()

if holdings_df.empty:
    st.info("No holdings yet. Use the sidebar to add your first position.")
else:
    df = holdings_df.copy()
    df["company_name"] = df["ticker"].map(lambda t: COMPANIES.get(t, {}).get("name", t))
    df["t12m_div_per_share"] = df["ticker"].apply(lambda t: trailing_12m_dividend(t, dividends_df))
    df["annual_income"] = df["shares_owned"] * df["t12m_div_per_share"]
    df["yield_on_cost"] = df.apply(
        lambda r: (r["t12m_div_per_share"] / r["average_buy_price"] * 100)
        if r["average_buy_price"] > 0 else 0.0, axis=1)
    df["position_value"] = df["shares_owned"] * df["average_buy_price"]

    total_income = df["annual_income"].sum()
    total_invested = df["position_value"].sum()
    portfolio_yoc = (total_income / total_invested * 100) if total_invested > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested (KES)", f"{total_invested:,.0f}")
    col2.metric("Trailing 12m Income (KES)", f"{total_income:,.0f}")
    col3.metric("Portfolio Yield on Cost", f"{portfolio_yoc:.2f}%")

    st.divider()
    display = df[["ticker", "company_name", "shares_owned", "average_buy_price",
                  "t12m_div_per_share", "yield_on_cost", "annual_income"]].copy()
    display.columns = ["Ticker", "Company", "Shares", "Avg Price (KES)",
                       "T12m Div/Share (KES)", "Yield on Cost (%)", "Annual Income (KES)"]
    for c in ["Avg Price (KES)", "T12m Div/Share (KES)", "Yield on Cost (%)"]:
        display[c] = display[c].round(2)
    display["Annual Income (KES)"] = display["Annual Income (KES)"].round(0)
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("### Annual Income by Company")
    chart_df = df[["ticker", "annual_income"]].sort_values("annual_income", ascending=True)
    fig = go.Figure(go.Bar(x=chart_df["annual_income"], y=chart_df["ticker"], orientation="h",
                           marker_color="#2ca02c",
                           text=[f"{v:,.0f} KES" for v in chart_df["annual_income"]],
                           textposition="outside"))
    fig.update_layout(template="plotly_dark", height=max(220, 40 * len(chart_df)),
                      margin=dict(l=10, r=60, t=10, b=10),
                      xaxis_title="Annual Income (KES)", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
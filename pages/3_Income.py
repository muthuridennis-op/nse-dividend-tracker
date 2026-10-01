# pages/3_Income.py
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


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
def fetch_income():
    resp = supabase.table("nse_income_received").select("*").order("payment_date", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


st.title("💰 Income Received")
st.caption("Dividend income log and cumulative tracking")

income_df = fetch_income()

if income_df.empty:
    st.info("No dividends recorded yet. Use the Holdings page sidebar to log them.")
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
    inc["cumulative"] = inc["amount_received"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=inc["payment_date"], y=inc["cumulative"],
                             mode="lines+markers", line=dict(color="#2ca02c", width=2),
                             name="Cumulative Income"))
    fig.update_layout(template="plotly_dark", height=280,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Date", yaxis_title="Cumulative Income (KES)")
    st.plotly_chart(fig, use_container_width=True)

    display_inc = inc[["ticker", "payment_date", "amount_received", "withholding_tax"]].copy()
    display_inc.columns = ["Ticker", "Payment Date", "Amount (KES)", "Tax (KES)"]
    display_inc["Payment Date"] = display_inc["Payment Date"].dt.strftime("%Y-%m-%d")
    display_inc["Amount (KES)"] = display_inc["Amount (KES)"].round(2)
    display_inc["Tax (KES)"] = display_inc["Tax (KES)"].fillna(0).round(2)
    st.dataframe(display_inc, use_container_width=True, hide_index=True)
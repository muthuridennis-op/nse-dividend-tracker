# pages/2_📅_Calendar.py
import os
import streamlit as st
import pandas as pd
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
def fetch_dividends():
    resp = supabase.table("nse_dividends").select("*").order("ex_date", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

st.title("📅 Ex-Dividend Calendar")
st.caption("Upcoming and recent dividend dates")

dividends_df = fetch_dividends()

if dividends_df.empty:
    st.info("No dividend data yet. Run the fetcher workflow first.")
else:
    div = dividends_df.copy()
    div["ex_date"] = pd.to_datetime(div["ex_date"], errors="coerce")
    today = pd.Timestamp.today().normalize()

    upcoming = div[div["ex_date"] >= today].sort_values("ex_date").head(20)
    past = div[div["ex_date"] < today].sort_values("ex_date", ascending=False).head(20)

    st.subheader("Upcoming Ex-Dividend Dates")
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
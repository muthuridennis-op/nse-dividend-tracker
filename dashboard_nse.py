# dashboard_nse.py
import streamlit as st
import pandas as pd
from database import DatabaseManager

db = DatabaseManager()
st.title("🇰🇪 NSE Dividend Tracker")

tab1, tab2, tab3 = st.tabs(["📊 My Holdings", "📅 Ex-Dividend Calendar", "💰 Income Received"])

with tab1:
    holdings = db.client.table("nse_holdings").select("*").execute().data
    if holdings:
        df = pd.DataFrame(holdings)
        df["annual_dividend"] = df.apply(
            lambda r: get_annual_dividend(r["ticker"]) * r["shares_owned"], axis=1
        )
        df["yield_on_cost"] = df.apply(
            lambda r: (get_annual_dividend(r["ticker"]) / r["average_buy_price"]) * 100, axis=1
        )
        st.dataframe(df)
        st.metric("Total Annual Income (KES)", f"{df['annual_dividend'].sum():,.2f}")
        st.metric("Average Yield on Cost", f"{df['yield_on_cost'].mean():.2f}%")

with tab2:
    upcoming = db.client.table("nse_dividends") \
        .select("*") \
        .gte("ex_date", "today") \
        .order("ex_date") \
        .execute().data
    st.dataframe(pd.DataFrame(upcoming))

with tab3:
    income = db.client.table("nse_income_received") \
        .select("*") \
        .order("payment_date", desc=True) \
        .execute().data
    if income:
        df = pd.DataFrame(income)
        st.bar_chart(df.groupby("payment_date")["amount_received"].sum())
# dashboard_nse.py
"""
NSE Dividend Tracker — entrypoint and router.
Each page lives in the pages/ folder.
"""
import streamlit as st

# Page config — shared across all pages
st.set_page_config(
    page_title="NSE Dividend Tracker",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optional: hide Streamlit chrome when embedded
if st.query_params.get("embed") == "true":
    st.markdown(
        """
        <style>
            #MainMenu {visibility: hidden;}
            header[data-testid="stHeader"] {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none;}
            .block-container {padding-top: 1rem; padding-bottom: 1rem;}
            button[title="View fullscreen"] {display: none !important;}
            button[title="Exit fullscreen"] {display: none !important;}
            [data-testid="stAppEmbedFullScreenButton"] {display: none !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Define pages
pages = [
    st.Page("pages/1_📊_Holdings.py", title="Holdings", icon="📊", default=True),
    st.Page("pages/2_📅_Calendar.py", title="Calendar", icon="📅"),
    st.Page("pages/3_💰_Income.py", title="Income", icon="💰"),
]

# Register navigation
pg = st.navigation(pages)
pg.run()
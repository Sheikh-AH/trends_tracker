"""
Keyword Deep Dive - Detailed analytics for individual keywords.
"""

import random
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

# Import shared functions from utils module
from utils import (
    get_db_connection,
    get_user_keywords,
)
from psycopg2.extras import RealDictCursor

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Keyword Deep Dive - Trends Tracker",
        page_icon="🔍",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()

def load_keywords():
    """Load keywords from database if needed."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else ["matcha", "boba", "coffee"]
            st.session_state.keywords_loaded = True

if __name__ == "__main__":
    pass




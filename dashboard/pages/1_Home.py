"""
Home - Welcome and introduction page for Trends Tracker.
"""

import streamlit as st

# Import shared functions from utils module
import sys
sys.path.insert(0, '..')
from utils import get_db_connection, get_user_keywords
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============
def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Welcome - Trends Tracker",
        page_icon="🏠",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Hide Sidebar ==============
def hide_sidebar():
    """Hide the sidebar on this page."""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)


# ============== Load Keywords ==============
def load_keywords():
    """Load user keywords from database."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True


# ============== Main Function ==============
def main():
    """Main function for the Welcome page."""
    hide_sidebar()

    # Welcome header
    st.title("🎉 Welcome to Trends Tracker!")
    st.markdown(f"### Hello, {st.session_state.get('username', 'User')}!")

    st.markdown("---")

    # Introduction section
    st.markdown("""
    ## What is Trends Tracker?

    Trends Tracker is your comprehensive social media analytics platform that helps you:

    - 📊 **Track Keywords**: Monitor trending topics and keywords across Bluesky and Google Trends
    - 🔍 **Deep Dive Analytics**: Get detailed insights into keyword performance, sentiment, and engagement
    - 🤖 **AI-Powered Insights**: Receive intelligent recommendations and trend analysis
    - 🔔 **Smart Alerts**: Stay notified about important changes and trending patterns

    """)

    st.markdown("---")

    # Load keywords to check if user has set them up
    load_keywords()
    has_keywords = len(st.session_state.get("keywords", [])) > 0

    # Getting Started section
    st.markdown("## 🚀 Getting Started")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 Step 1: Set Up Keywords")
        st.markdown("""
        Start by adding the keywords and topics you want to track.
        These can be brands, products, hashtags, or any topics of interest.
        """)

        if st.button("🏷️ Manage Topics", type="primary", use_container_width=True):
            st.switch_page("pages/5_Manage_Topics.py")

    with col2:
        st.markdown("### 📊 Step 2: Explore Analytics")
        st.markdown("""
        Once you've added keywords, dive into the analytics to see
        trends, sentiment analysis, and engagement metrics.
        """)

        if has_keywords:
            if st.button("📈 View Semantics", type="primary", use_container_width=True):
                st.switch_page("pages/2_Semantics.py")
        else:
            st.button("📈 View Semantics", disabled=True, use_container_width=True)
            st.caption("⚠️ Add keywords first to view analytics")

    st.markdown("---")

    # Feature cards
    st.markdown("## ✨ Key Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📊 Semantics Dashboard
        Visualize trends over time with interactive charts,
        word clouds, and sentiment analysis.
        """)
        if has_keywords:
            if st.button("Go to Semantics", key="semantics_bottom", use_container_width=True):
                st.switch_page("pages/2_Semantics.py")
        else:
            st.button("Go to Semantics", disabled=True, key="semantics_bottom_disabled", use_container_width=True)

    with col2:
        st.markdown("""
        ### 🔍 Keyword Deep Dive
        Get detailed analytics for individual keywords with
        comprehensive performance metrics.
        """)
        if has_keywords:
            if st.button("Deep Dive Analysis", key="deepdive_bottom", use_container_width=True):
                st.switch_page("pages/3_Keyword_Deep_Dive.py")
        else:
            st.button("Deep Dive Analysis", disabled=True, key="deepdive_bottom_disabled", use_container_width=True)

    with col3:
        st.markdown("""
        ### 🤖 AI Insights
        Leverage AI-powered analysis to discover patterns,
        themes, and actionable recommendations.
        """)
        if has_keywords:
            if st.button("AI Insights", key="ai_bottom", use_container_width=True):
                st.switch_page("pages/4_AI_Insights.py")
        else:
            st.button("AI Insights", disabled=True, key="ai_bottom_disabled", use_container_width=True)

    st.markdown("---")

    # Status indicator
    if has_keywords:
        st.success(f"✅ You're tracking {len(st.session_state.keywords)} keyword(s). Ready to explore!")
    else:
        st.info("👉 Get started by adding some keywords to track!")

    # Quick stats if keywords exist
    if has_keywords:
        st.markdown("### 📋 Your Keywords")
        keywords_display = ", ".join([f"`{kw}`" for kw in st.session_state.keywords])
        st.markdown(keywords_display)


# ============== Entry Point ==============
configure_page()
main()

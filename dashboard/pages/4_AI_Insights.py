"""
AI Insights - LLM-generated summaries and recommendations for keywords.
"""

import streamlit as st

# Import shared functions from utils module
import sys
from utils import (
    get_db_connection,
    get_user_keywords,
    generate_ai_insights,
    render_sidebar
)
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="AI Insights - Trends Tracker",
        page_icon="🤖",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Helper Functions ==============

def load_keywords():
    """Load keywords from database if needed."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True


def render_executive_summary(summary: str):
    """Render the executive summary section."""
    st.markdown("### 📝 Executive Summary")

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin-bottom: 20px;
    ">
        <p style="font-size: 1.1em; line-height: 1.7; color: #333; margin: 0;">
            {summary}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_themes(themes: list):
    """Render the key themes section."""
    st.markdown("### 🎯 Key Themes Detected")

    for i, theme in enumerate(themes, 1):
        st.markdown(f"""
        <div style="
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 10px;
            border: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
        ">
            <span style="
                background: #667eea;
                color: white;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-weight: bold;
            ">{i}</span>
            <span style="font-size: 1.05em;">{theme}</span>
        </div>
        """, unsafe_allow_html=True)


def render_sentiment_drivers(sentiment_drivers: dict):
    """Render the sentiment drivers section."""
    st.markdown("### 📊 Sentiment Drivers")

    # Positive drivers
    st.markdown("**⬆️ Positive Drivers**")
    for driver in sentiment_drivers['positive']:
        st.markdown(f"""
        <div style="
            background: #d4edda;
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 8px;
            border-left: 4px solid #28a745;
        ">
            ✅ {driver}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")  # Spacer

    # Negative drivers
    st.markdown("**⬇️ Negative Drivers**")
    for driver in sentiment_drivers['negative']:
        st.markdown(f"""
        <div style="
            background: #f8d7da;
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 8px;
            border-left: 4px solid #dc3545;
        ">
            ⚠️ {driver}
        </div>
        """, unsafe_allow_html=True)


def render_recommendations(recommendations: list):
    """Render the recommendations section."""
    st.markdown("### 💡 Recommended Actions")

    for rec in recommendations:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            border: 1px solid #667eea44;
        ">
            <div style="display: flex; align-items: flex-start;">
                <span style="
                    font-size: 1.5em;
                    margin-right: 15px;
                ">💡</span>
                <div>
                    <p style="margin: 0; font-size: 1.05em; color: #333;">
                        {rec}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============== Main Function ==============

def main():
    """Main function for the AI Insights page."""
    st.title("🤖 AI Insights")
    st.markdown("AI-powered analysis and recommendations for your tracked keywords.")

    # Load keywords
    load_keywords()

    # Top controls row
    col1, col2, _ = st.columns([2, 2, 4])

    with col1:
        keywords = st.session_state.get("keywords", [])
        if keywords:
            selected_keyword = st.selectbox("Select Keyword", options=keywords, index=0)
        else:
            st.warning("No keywords tracked. Add some in Manage Topics.")
            st.stop()

    with col2:
        days_options = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}
        selected_period = st.selectbox("Time Period", options=list(days_options.keys()))
        days = days_options[selected_period]

    st.markdown("---")

    # Get AI insights
    insights = generate_ai_insights(selected_keyword, days)

    # Executive Summary Section
    render_executive_summary(insights['summary'])

    st.markdown("---")

    # Themes and Sentiment Drivers in columns
    col1, col2 = st.columns(2)

    with col1:
        render_themes(insights['themes'])

    with col2:
        render_sentiment_drivers(insights['sentiment_drivers'])

    st.markdown("---")

    # Recommendations Section
    render_recommendations(insights['recommendations'])

    # Default Sidebar
    # Render shared sidebar
    render_sidebar()


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
if __name__ == "__main__":
    configure_page()
    main()
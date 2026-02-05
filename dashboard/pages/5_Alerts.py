"""
Alerts - Notification and alert management dashboard.
"""

import pandas as pd
import streamlit as st

# Import shared functions from main app
import sys
sys.path.insert(0, '..')
from app import get_db_connection, get_user_keywords
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Alerts - Trends Tracker",
        page_icon="🔔",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Helper Functions ==============

def initialize_alert_state():
    """Initialize session state for alerts."""
    if "alerts_enabled" not in st.session_state:
        st.session_state.alerts_enabled = False
    if "alert_email" not in st.session_state:
        st.session_state.alert_email = ""


def load_keywords():
    """Load keywords from database if needed."""
    if "keywords_loaded" not in st.session_state:
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True


def render_email_alerts_section():
    """Render the email alerts section."""
    st.markdown("### 📧 Email Alerts")

    alerts_enabled = st.toggle(
        "Enable Email Alerts",
        value=st.session_state.alerts_enabled,
        help="Receive email notifications for significant trend changes"
    )
    st.session_state.alerts_enabled = alerts_enabled

    if alerts_enabled:
        email = st.text_input(
            "Email Address",
            value=st.session_state.alert_email,
            placeholder="your@email.com"
        )
        st.session_state.alert_email = email


def render_alert_preferences_section():
    """Render the alert preferences section."""
    st.markdown("### ⚙️ Alert Preferences")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Notification Triggers**")
        st.checkbox("Sudden spike in mentions (>50% increase)", value=True)
        st.checkbox("Significant sentiment shift", value=True)
        st.checkbox("New trending hashtag related to keyword", value=False)
        st.checkbox("Keyword mentioned by influencer", value=False)

    with col2:
        st.markdown("**Notification Frequency**")
        st.radio(
            "How often should we send alerts?",
            options=["Real-time", "Hourly digest", "Daily summary"],
            index=1
        )


def render_keyword_monitoring_section():
    """Render the keyword monitoring section."""
    st.markdown("### 🔔 Keywords to Monitor")

    keywords = st.session_state.get("keywords", [])
    if keywords:
        for keyword in keywords:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.checkbox(f"Monitor: **{keyword}**", value=True, key=f"alert_{keyword}")
            with col2:
                st.selectbox(
                    "Priority",
                    options=["High", "Medium", "Low"],
                    index=1,
                    key=f"priority_{keyword}",
                    label_visibility="collapsed"
                )
    else:
        st.info("No keywords to monitor. Add keywords in the Manage Topics page.")


def render_alert_history_section():
    """Render the alert history section."""
    st.markdown("### 📜 Recent Alert History")

    placeholder_alerts = pd.DataFrame({
        "Date": ["2026-02-05", "2026-02-04", "2026-02-03", "2026-02-02"],
        "Keyword": ["matcha", "boba", "matcha", "coffee"],
        "Alert Type": ["Spike", "Sentiment", "Trending", "Spike"],
        "Message": [
            "50% increase in mentions detected",
            "Sentiment shifted from neutral to positive",
            "Appeared in #trending topics",
            "75% increase in mentions detected"
        ],
        "Status": ["Sent", "Sent", "Sent", "Sent"]
    })

    def style_status(val):
        if val == "Sent":
            return "background-color: #d4edda; color: #155724;"
        return ""

    styled_alerts = placeholder_alerts.style.map(style_status, subset=["Status"])
    st.dataframe(styled_alerts, use_container_width=True, hide_index=True)


def render_coming_soon_section():
    """Render the coming soon section."""
    st.markdown("### 🚀 Coming Soon")
    st.markdown("""
    **Planned Alert Features:**
    - SMS notifications
    - Slack/Discord webhooks
    - Custom alert thresholds
    - Scheduled reports (weekly/monthly)
    - Alert analytics and history

    *Stay tuned for updates!*
    """)


# ============== Main Function ==============

def main():
    """Main function for the Alerts page."""
    st.title("🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")

    st.markdown("---")

    # Initialize state
    initialize_alert_state()
    load_keywords()

    # Email alerts section
    render_email_alerts_section()

    st.markdown("---")

    # Alert preferences
    render_alert_preferences_section()

    st.markdown("---")

    # Keyword monitoring
    render_keyword_monitoring_section()

    st.markdown("---")

    # Alert history
    render_alert_history_section()

    st.markdown("---")

    # Coming soon
    render_coming_soon_section()

    # Default Sidebar
    with st.sidebar:
        st.markdown(f"### 👋 Hello, {st.session_state.get('username', 'User')}!")
        st.markdown("---")
        st.markdown("### 📈 Quick Stats")
        st.metric("Keywords Tracked", len(st.session_state.get("keywords", [])))
        st.metric("Alerts Enabled", "Yes" if st.session_state.get("alerts_enabled", False) else "No")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_id = None
            st.switch_page("app.py")
        st.markdown("---")
        st.caption("Trends Tracker v1.0")


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
configure_page()
main()

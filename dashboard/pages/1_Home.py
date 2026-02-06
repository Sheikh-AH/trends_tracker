"""Home - Welcome and introduction page for Trends Tracker."""

from utils import (
    get_db_connection,
    get_user_keywords,
    add_user_keyword,
    remove_user_keyword,
)
from psycopg2.extras import RealDictCursor
import sys
import streamlit as st
from streamlit import session_state as ss

sys.path.insert(0, '..')


def configure_page():
    """Configure page settings and check authentication."""
    if 'sidebar_state' not in ss:
        ss.sidebar_state = 'collapsed'

    st.set_page_config(
        page_title="TrendsFunnel",
        page_icon="images/logo_blue.svg",
        layout="wide",
        initial_sidebar_state=ss.sidebar_state
    )

    # Check authentication
    if "logged_in" not in ss or not ss.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


def load_styled_component(filepath: str) -> str:
    """Load HTML/CSS styling from a file."""
    try:
        with open(filepath, 'r') as f:
            styling = f.read()
            return styling
    except FileNotFoundError:
        return st.error("Error loading styled component.")


def load_keywords():
    """Load user keywords from database."""
    if not ss.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and ss.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, ss.user_id)
            cursor.close()
            ss.keywords = db_keywords if db_keywords else []
            ss.keywords_loaded = True


def add_logo_and_title():
    """Add logo and title to the page."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_img_spacer, col_img, col_text = st.columns(
            [0.3, 0.2, 1], gap="small")
        with col_img:
            st.image("images/logo_blue.svg", width=100)
        with col_text:
            st.markdown(
                load_styled_component("styling/home_title.html"),
                unsafe_allow_html=True)
            st.markdown(
                load_styled_component("styling/home_tagline.html"),
                unsafe_allow_html=True)


def render_add_keyword_section():
    """Render the add keyword section."""
    col1, col2 = st.columns([3, 1])

    with col1:
        new_keyword = st.text_input(
            "Enter keyword",
            placeholder="e.g. matcha, tea, boba...",
            label_visibility="collapsed"
        )

    with col2:
        if st.button("Add Keyword", use_container_width=True, type="primary"):
            if new_keyword and new_keyword.strip():
                keyword_clean = new_keyword.strip().lower()
                if keyword_clean not in ss.keywords:
                    # Add to database
                    conn = get_db_connection()
                    if conn and ss.get("user_id"):
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        add_user_keyword(
                            cursor, ss.user_id, keyword_clean)
                        conn.commit()
                        cursor.close()
                        ss.keywords.append(keyword_clean)
                        st.success(
                            f"Added '{keyword_clean}' to your keywords!")
                        st.rerun()
                else:
                    st.warning(f"'{keyword_clean}' is already in your list.")
            else:
                st.warning("Please enter a valid keyword.")


def render_keywords_display():
    """Render the current keywords display."""

    keywords = ss.get("keywords", [])
    if keywords:
        # Display in a grid
        cols = st.columns(4)
        for i, keyword in enumerate(keywords):
            with cols[i % 4]:
                styling = load_styled_component("styling/home_keywords.html")
                st.markdown(styling.format(keyword=keyword),
                            unsafe_allow_html=True)

                if st.button(f"🗑️ Remove", key=f"remove_{keyword}", use_container_width=True):
                    # Remove from database
                    conn = get_db_connection()
                    if conn and ss.get("user_id"):
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        remove_user_keyword(
                            cursor, ss.user_id, keyword)
                        conn.commit()
                        cursor.close()
                        ss.keywords.remove(keyword)
                        st.success(f"Removed '{keyword}'")
                        st.rerun()
    else:
        st.info("No keywords added yet. Add some above to start tracking!")


def render_what_is_trends_tracker():
    """Render the 'What is Trends Tracker?' section."""
    with st.expander("## What is Trends Tracker?"):
        st.markdown("""
        Trends Tracker is your comprehensive social media analytics platform that helps you:

        - **Track Keywords**: Monitor trending topics and keywords across Bluesky and Google Trends
        - **Deep Dive Analytics**: Get detailed insights into keyword performance, sentiment, and engagement
        - **AI-Powered Insights**: Receive intelligent recommendations and trend analysis
        - **Smart Alerts**: Stay notified about important changes and trending patterns
        """)


def render_getting_started(has_keywords):
    with st.expander("Getting Started"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Step 1: Set Up Keywords")
            st.markdown("""
            Start by adding the keywords and topics you want to track.
            These can be brands, products, or any topics of interest.
            """)

        with col2:
            st.markdown("### Step 2: Explore Analytics")
            st.markdown("""
            Once you've added keywords, dive into the analytics to see
            trends, sentiment analysis, and engagement metrics.
            """)

        with col3:
            st.markdown("### Step 3: Set Up Alerts")
            st.markdown("""
            Stay informed with smart alerts that notify you about significant 
            changes in trends or sentiment for your tracked keywords.
            """)
    
def render_semantics_card():
    """Render the Semantics Dashboard card."""
    st.markdown("""
    ### Semantics Dashboard
    Visualize trends over time with interactive charts,
    word clouds, and sentiment analysis.
    """)
    if st.button("📊 Go to Semantics", key="semantics_top", use_container_width=True):
        st.switch_page("pages/2_Semantics.py")

def render_deep_dive_card():
    """Render the Keyword Deep Dive card."""
    st.markdown("""
    ### Keyword Deep Dive
    Get detailed analytics for individual keywords with
    comprehensive performance metrics.
    """)
    if st.button("🔍 Deep Dive Analysis", key="deepdive_top", use_container_width=True):
        st.switch_page("pages/3_Keyword_Deep_Dive.py")

def render_daily_summary_card():
    """Render the Daily Summary card."""
    st.markdown("""
    ### Daily Summary
    Leverage AI-powered analysis to discover daily patterns,
    and themes for your keywords.
    """)
    if st.button("📅 Daily Summary", key="ai_top", use_container_width=True):
        st.switch_page("pages/4_AI_Insights.py")

def render_keyword_comparisons_card():
    """Render the Keyword Comparisons card."""
    st.markdown("""
    ### Keyword Comparisons
    Compare multiple keywords side-by-side to identify trends
     and competitive insights.
    """)
    if st.button("⚡ Keyword Comparisons", key="comparisons_top", use_container_width=True):
        st.switch_page("pages/5_Keyword_Comparisons.py")

if __name__ == "__main__":

    configure_page()
    
    # Custom CSS for buttons and fonts
    styling = load_styled_component("styling/home_font_buttons.html")
    st.markdown(styling, unsafe_allow_html=True)

    # Check for user keywords
    load_keywords()
    has_keywords = len(ss.get("keywords", [])) > 0

    st.space("xlarge")
    add_logo_and_title()
    st.space("medium")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        render_add_keyword_section()
        st.space('medium')
        render_keywords_display()

    st.space('medium')

    render_what_is_trends_tracker()

    render_getting_started(has_keywords)

    st.markdown("---")

    # Feature cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_semantics_card()
    with col2:
        render_deep_dive_card()
    with col3:
        render_daily_summary_card()
    with col4:
        render_keyword_comparisons_card()

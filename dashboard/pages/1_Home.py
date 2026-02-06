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


if 'sidebar_state' not in ss:
    ss.sidebar_state = 'collapsed'


def change():
    ss.sidebar_state = (
        "collapsed" if ss.sidebar_state == "expanded" else "expanded"
    )


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


def hide_sidebar():
    """Hide the sidebar on this page."""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)


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
                "<h1 style='font-family: Ubuntu, sans-serif; margin: 0; padding-top: 10px; font-weight: bold; font-size: 50px; margin-bottom: -20px;'>TrendFunnel</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='font-family: Ubuntu, sans-serif; margin: 0; padding-top: 0px; font-style: italic; font-size: 15px; color: #555555;'>Turning fuzz into biz</p>",
                unsafe_allow_html=True,
            )


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
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 10px;
                    font-size: 1.1em;
                ">
                    {keyword}
                </div>
                """, unsafe_allow_html=True)

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

# ============== Main Function ==============


def main():
    """Main function for the Welcome page."""
    # Custom CSS for buttons and fonts
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;700&display=swap');
        
        /* Style secondary/regular buttons (Remove and Feature buttons) */
        .stButton > button:not([kind="primary"]) {
            background-color: rgba(25, 118, 210, 0.2) !important;
            color: #1976D2 !important;
            border: 1px solid rgba(25, 118, 210, 0.5) !important;
        }
        .stButton > button:not([kind="primary"]):hover {
            background-color: rgba(25, 118, 210, 0.5) !important;
        }
        
        h1, h2, h3, p {
            font-family: 'Ubuntu', sans-serif !important;
        }
        </style>
    """, unsafe_allow_html=True)

    load_keywords()
    # hide_sidebar()
    has_keywords = len(ss.get("keywords", [])) > 0

    # Add vertical space
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

    add_logo_and_title()

    st.space("medium")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        render_add_keyword_section()
        st.space('medium')
        render_keywords_display()

    st.space('medium')

    # Introduction section
    render_what_is_trends_tracker()

    # Getting Started section
    render_getting_started(has_keywords)

    st.markdown("---")

    # Feature cards
    # st.markdown("## Key Features")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        ### Semantics Dashboard
        Visualize trends over time with interactive charts,
        word clouds, and sentiment analysis.
        """)
        if has_keywords:
            if st.button("📊 Go to Semantics", key="semantics_bottom", use_container_width=True):
                st.switch_page("pages/2_Semantics.py")
        else:
            st.button("📊 Go to Semantics", disabled=True,
                      key="semantics_bottom_disabled", use_container_width=True)

    with col2:
        st.markdown("""
        ### Keyword Deep Dive
        Get detailed analytics for individual keywords with
        comprehensive performance metrics.
        """)
        if has_keywords:
            if st.button("🔍 Deep Dive Analysis", key="deepdive_bottom", use_container_width=True):
                st.switch_page("pages/3_Keyword_Deep_Dive.py")
        else:
            st.button("🔍 Deep Dive Analysis", disabled=True,
                      key="deepdive_bottom_disabled", use_container_width=True)

    with col3:
        st.markdown("""
        ### Daily Summary
        Leverage AI-powered analysis to discover daily patterns,
        and themes for your keywords.
        """)
        if has_keywords:
            if st.button("📅 Daily Summary", key="ai_bottom", use_container_width=True):
                st.switch_page("pages/4_AI_Insights.py")
        else:
            st.button("📅 Daily Summary", disabled=True,
                      key="ai_bottom_disabled", use_container_width=True)

    with col4:
        st.markdown("""
        ### Keyword Comparisons
        Compare multiple keywords side-by-side to identify trends
         and competitive insights.
        """)
        if has_keywords:
            if st.button("⚡ Keyword Comparisons", key="comparisons_bottom", use_container_width=True):
                st.switch_page("pages/5_Keyword_Comparisons.py")
        else:
            st.button("⚡ Keyword Comparisons", disabled=True,
                      key="comparisons_bottom_disabled", use_container_width=True)


main()

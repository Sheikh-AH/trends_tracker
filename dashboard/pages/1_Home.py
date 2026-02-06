"""Home - Welcome and introduction page for Trends Tracker."""

from psycopg2.extras import RealDictCursor
import sys
import streamlit as st

sys.path.insert(0, '..')

from utils import (
    get_db_connection,
    get_user_keywords,
    add_user_keyword,
    remove_user_keyword,
)

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Welcome - Trends Tracker",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
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
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True


def add_logo_and_title():
    """Add logo and title to the page."""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        col_img, col_text = st.columns([0.3, 1], gap="small")
        with col_img:
            st.image("images/logo_blue.svg", width=250)
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
    # st.markdown("### ➕ Add New Keyword")
    col1, col2 = st.columns([3, 1])

    with col1:
        new_keyword = st.text_input(
            "Enter keyword",
            placeholder="e.g., matcha, tea, boba...",
            label_visibility="collapsed"
        )

    with col2:
        if st.button("Add Keyword", use_container_width=True, type="primary"):
            if new_keyword and new_keyword.strip():
                keyword_clean = new_keyword.strip().lower()
                if keyword_clean not in st.session_state.keywords:
                    # Add to database
                    conn = get_db_connection()
                    if conn and st.session_state.get("user_id"):
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        add_user_keyword(
                            cursor, st.session_state.user_id, keyword_clean)
                        conn.commit()
                        cursor.close()
                        st.session_state.keywords.append(keyword_clean)
                        st.success(
                            f"Added '{keyword_clean}' to your keywords!")
                        st.rerun()
                else:
                    st.warning(f"'{keyword_clean}' is already in your list.")
            else:
                st.warning("Please enter a valid keyword.")


def render_keywords_display():
    """Render the current keywords display."""

    keywords = st.session_state.get("keywords", [])
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
                    if conn and st.session_state.get("user_id"):
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        remove_user_keyword(
                            cursor, st.session_state.user_id, keyword)
                        conn.commit()
                        cursor.close()
                        st.session_state.keywords.remove(keyword)
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
    hide_sidebar()
    load_keywords()
    has_keywords = len(st.session_state.get("keywords", [])) > 0

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
    st.markdown("## Key Features")

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
            st.button("Go to Semantics", disabled=True,
                      key="semantics_bottom_disabled", use_container_width=True)

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
            st.button("Deep Dive Analysis", disabled=True,
                      key="deepdive_bottom_disabled", use_container_width=True)

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
            st.button("AI Insights", disabled=True,
                      key="ai_bottom_disabled", use_container_width=True)



if __name__ == "__main__":
    configure_page()
    main()

"""Manage Topics - Keyword management dashboard."""

import streamlit as st

# Import shared functions from utils module
import sys
import logging
from dotenv import load_dotenv
from utils import (
    get_db_connection,
    get_user_keywords,
    add_user_keyword,
    remove_user_keyword,
    render_sidebar
)
from alerts import render_alerts_dashboard
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Manage Topics - Trends Tracker",
        page_icon="🏷️",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


def load_keywords():
    """Load keywords from database on first visit."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True

    # Initialize keywords if not present
    if "keywords" not in st.session_state:
        st.session_state.keywords = []


def render_add_keyword_section():
    """Render the add keyword section."""
    st.markdown("##### ➕ Add New Keyword")
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
                        add_user_keyword(cursor, st.session_state.user_id, keyword_clean)
                        conn.commit()
                        cursor.close()
                        st.session_state.keywords.append(keyword_clean)
                        st.success(f"Added '{keyword_clean}' to your keywords!")
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
                        remove_user_keyword(cursor, st.session_state.user_id, keyword)
                        conn.commit()
                        cursor.close()
                        st.session_state.keywords.remove(keyword)
                        st.success(f"Removed '{keyword}'")
                        st.rerun()
    else:
        st.info("No keywords added yet. Add some above to start tracking!")


if __name__ == "__main__":
    configure_page()
    render_sidebar()
    conn = get_db_connection()
    load_dotenv()

    st.markdown("---")

    st.markdown("### 🏷️ Topics Management")
    st.markdown("Manage your tracked keywords and topics here.")

    load_keywords()
    st.markdown("---")

    render_add_keyword_section()
    st.markdown("---")

    render_keywords_display()
    st.markdown("---")

    render_alerts_dashboard(conn)

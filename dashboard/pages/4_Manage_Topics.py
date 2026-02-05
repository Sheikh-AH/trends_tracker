"""
Manage Topics - Keyword management dashboard.
"""

import streamlit as st

# Import shared functions from main app
import sys
sys.path.insert(0, '..')
from app import (
    get_db_connection,
    get_user_keywords,
    add_user_keyword,
    remove_user_keyword
)
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

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


# ============== Helper Functions ==============

def load_keywords():
    """Load keywords from database on first visit."""
    if "keywords_loaded" not in st.session_state:
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
    st.markdown("### ➕ Add New Keyword")
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
    st.markdown("### 📋 Your Keywords")

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


def render_tips_section():
    """Render the tips section."""
    st.markdown("### 💡 Tips for Effective Tracking")

    tips_col1, tips_col2 = st.columns(2)

    with tips_col1:
        st.markdown("""
        **Choosing Keywords:**
        - Use specific terms (e.g., "matcha latte" vs "tea")
        - Include brand names and hashtags
        - Consider misspellings and variations
        - Add competitor brand names
        """)

    with tips_col2:
        st.markdown("""
        **Best Practices:**
        - Start with 3-5 keywords
        - Review and refine regularly
        - Remove low-performing keywords
        - Add trending terms as they emerge
        """)


# ============== Main Function ==============

def main():
    """Main function for the Manage Topics page."""
    st.title("🏷️ Topics Management")
    st.markdown("Manage your tracked keywords and topics here.")

    st.markdown("---")

    # Load keywords
    load_keywords()

    # Add keyword section
    render_add_keyword_section()

    st.markdown("---")

    # Current keywords display
    render_keywords_display()

    st.markdown("---")

    # Tips section
    render_tips_section()

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

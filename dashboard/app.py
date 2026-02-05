"""
Trends Tracker Dashboard - Streamlit Mockup
A multi-page dashboard for tracking social media trends and analytics.
Sources of data are bluesky and Google trends.
"""

import logging
import streamlit as st
from psycopg2.extras import RealDictCursor

# Import shared utilities
from utils import (
    get_db_connection,
    get_db_connection_cleanup,
    get_user_by_username,
    authenticate_user,
    generate_password_hash,
    validate_signup_input,
    create_user
)

# ============== Logging Configuration ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register cleanup
_cleanup = get_db_connection_cleanup()


# ============== Page Configuration ==============
st.set_page_config(
    page_title="Trends Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============== Session State Initialization ==============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "emails_enabled" not in st.session_state:
    st.session_state.emails_enabled = False
if "alerts_enabled" not in st.session_state:
    st.session_state.alerts_enabled = False
if "email" not in st.session_state or not st.session_state.logged_in:
    st.session_state.email = ""


# ============== Login Page ==============
def show_login_page():
    """Display the login/signup page."""
    # Hide sidebar on login page
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔐 Trends Tracker")
    st.markdown("### Welcome! Please login or create an account to continue.")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.markdown("#### Login to Your Account")
        login_username = st.text_input("Username", key="login_username", placeholder="your_username")
        login_password = st.text_input("Password", type="password", key="login_password")

        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                if login_username and login_password:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        is_authenticated = authenticate_user(cursor, login_username, login_password)

                        if is_authenticated:
                            # Get user_id from database
                            user = get_user_by_username(cursor, login_username)
                            cursor.close()

                            st.session_state.logged_in = True
                            st.session_state.username = login_username
                            st.session_state.user_id = user["user_id"]
                            st.session_state.email = user["email"]
                            # Clear user-specific data from previous sessions
                            st.session_state.keywords = []
                            st.session_state.keywords_loaded = False
                            st.session_state.alerts_loaded = False
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            cursor.close()
                            st.error("Invalid username or password.")
                    else:
                        st.error("Unable to connect to database. Please try again later.")
                else:
                    st.error("Please enter both username and password.")

    with tab2:
        st.markdown("#### Create a New Account")
        signup_name = st.text_input("Full Name", key="signup_name", placeholder="John Doe")
        signup_email = st.text_input("Email", key="signup_email", placeholder="your@email.com")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("Sign Up", type="primary", use_container_width=True):
                if not signup_name:
                    st.error("Please enter your full name.")
                elif signup_password != signup_confirm:
                    st.error("Passwords do not match.")
                elif not validate_signup_input(signup_email, signup_password):
                    st.error("Email must be valid and password must be longer than 8 characters.")
                else:
                    # Hash the password and create the user
                    password_hash = generate_password_hash(signup_password)
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        user_created = create_user(cursor, signup_email, password_hash)

                        if user_created:
                            # Get the newly created user's ID
                            user = get_user_by_username(cursor, signup_email)
                            cursor.close()

                            st.session_state.logged_in = True
                            st.session_state.username = signup_name.split()[0]
                            st.session_state.user_id = user["user_id"]
                            st.session_state.email = user["email"]
                            # Clear user-specific data from previous sessions
                            st.session_state.keywords = []
                            st.session_state.keywords_loaded = False
                            st.session_state.alerts_loaded = False
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            cursor.close()
                            st.error("Email already exists. Please use a different email.")
                    else:
                        st.error("Unable to connect to database. Please try again later.")


# ============== Main App ==============
def main():
    """Main application entry point."""
    if not st.session_state.logged_in:
        show_login_page()
    else:
        st.switch_page("pages/1_Home.py")


if __name__ == "__main__":
    main()


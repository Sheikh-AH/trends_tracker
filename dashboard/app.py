"""Login Page and Main App Runner for Trends Tracker Dashboard."""

import logging
import streamlit as st
from streamlit import session_state as ss
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def configure_page() -> None:
    """Set up the Streamlit page configuration."""
    st.set_page_config(
        page_title="Trendfunnel",
        layout="wide",
        initial_sidebar_state="collapsed",
        page_icon="art/logo_blue.svg"
    )

def initialize_session_state() -> None:
    """Initialize session state variables for user authentication and data."""
    if "logged_in" not in ss:
        ss.logged_in = False

    if not ss.logged_in:
        ss.username = ""
        ss.user_id = None
        ss.email = ""
        ss.keywords = []
        ss.keywords_loaded = False
        ss.alerts_loaded = False
        ss.emails_enabled = False
        ss.alerts_enabled = False

def set_user_session(user: dict, conn) -> None:
    """Set session state variables for the logged-in user."""
    ss.logged_in = True
    ss.username = user["email"].split("@")[0]  # Use email prefix as username
    ss.user_id = user["user_id"]
    ss.email = user["email"]
    ss.db_conn = conn
    st.success("Login successful!")
    st.rerun()

def render_login_tab() -> None:
    """Render the login tab content."""

    st.space('xxsmall')
    login_username = st.text_input("Username", key="login_username", placeholder="username")
    login_password = st.text_input("Password", type="password", key="login_password", placeholder="password")
    st.space('xxsmall')

    try:
        conn = get_db_connection()
    except Exception as e:
        st.error("Unable to connect to database. Please try again later.")
        return

    col1, _ = st.columns([1, 3])
    with col1:
        if st.button("Login", type="primary", use_container_width=True):
            if login_username and login_password:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                is_authenticated = authenticate_user(cursor, login_username, login_password)
                cursor.close()
            else:
                st.error("Please enter both username and password.")
            if is_authenticated:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                user = get_user_by_username(cursor, login_username)
                cursor.close()
                set_user_session(user, conn)

            else:
                st.error("Invalid username or password.")

def new_account_fields() -> tuple:
    """Create input fields for new account registration and return the values."""
    st.space('xxsmall')
    signup_name = st.text_input(
        "Full Name", key="signup_name")
    signup_email = st.text_input(
        "Email", key="signup_email")
    signup_password = st.text_input(
        "Password", type="password", key="signup_password")
    signup_confirm = st.text_input(
        "Confirm Password", type="password", key="signup_confirm")
    st.space('xxsmall')
    return signup_name, signup_email, signup_password, signup_confirm

def render_get_new_account() -> None:
    """Render the sign-up tab content."""
    signup_name, signup_email, signup_password, signup_confirm = new_account_fields()

    col1, _ = st.columns([1, 3])
    with col1:
        if st.button("Sign Up", type="primary", use_container_width=True):
            if not signup_name:
                st.error("Please enter your full name.")
            elif signup_password != signup_confirm:
                st.error("Passwords do not match.")
            elif not validate_signup_input(signup_email, signup_password):
                st.error(
                    "Email must be valid and password must be longer than 8 characters.")
            else:
                # Hash the password and create the user
                password_hash = generate_password_hash(signup_password)
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                user_created = create_user(cursor, signup_email, password_hash)
                user = get_user_by_username(cursor, signup_email)
                cursor.close()

                ss.logged_in = True
                ss.username = signup_name.split()[0]
                ss.user_id = user["user_id"]
                ss.email = user["email"]
                ss.db_conn = conn
                ss.keywords = []
                ss.keywords_loaded = False
                ss.alerts_loaded = False
                st.success("Account created successfully!")
                st.rerun()


def show_login_page() -> None:
    """Display the login/signup page."""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        # Logo and title
        col_img, col_text = st.columns([0.2, 1], gap="small")
        with col_img:
            st.image("art/logo_blue.svg", width=100)
        with col_text:
            st.title("Trendfunnel")
            st.caption("Turning fuzz into biz")

        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            render_login_tab()

        with tab2:
            render_get_new_account()


def create_nav() -> st.Navigation:
    """Create the navigation menu for logged-in users."""
    return st.navigation(
        [
            st.Page("pages/1_Home.py", title="Home"),
            st.Page("pages/2_Semantics.py", title="Semantics"),
            st.Page("pages/3_Daily_Summary.py", title="Daily Summary"),
            st.Page("pages/3_Keyword_Deep_Dive.py", title="Keyword Deep Dive"),
            st.Page("pages/4_AI_Insights.py", title="AI Insights"),
            st.Page("pages/5_Profile.py", title="Profile"),
        ]
    )

if __name__ == "__main__":

    configure_page()
    initialize_session_state()

    if not st.session_state.logged_in:
        show_login_page()
    else:
        nav = create_nav()
        nav.run()

    # Register cleanup
    _cleanup = get_db_connection_cleanup()

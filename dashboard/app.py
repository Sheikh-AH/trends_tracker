"""
Trends Tracker Dashboard - Streamlit Mockup
A multi-page dashboard for tracking social media trends and analytics.
"""

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta
from os import environ as ENV, _Environ
from typing import Optional
import random

import altair as alt
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from dotenv import load_dotenv

# ============== Logging Configuration ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== Environment Configuration ==============
load_dotenv()

# ============== Database Configuration ==============
DB_CONFIG = {
    "host": ENV.get("DB_HOST"),
    "port": int(ENV.get("DB_PORT", 5432)),
    "database": ENV.get("DB_NAME"),
    "user": ENV.get("DB_USER"),
    "password": ENV.get("DB_PASSWORD")
}

@st.cache_resource
def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """Get persistent database connection for the entire session."""
    conn = psycopg2.connect(
        host=DB_CONFIG.get("host"),
        port=DB_CONFIG.get("port", 5432),
        database=DB_CONFIG.get("database"),
        user=DB_CONFIG.get("user"),
        password=DB_CONFIG.get("password")
    )
    logger.info("Database connection established.")
    return conn


def get_user_by_username(cursor, email: str) -> Optional[dict]:
    """Retrieve user details from database by username."""
    query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    return result


def verify_password(stored_hash: str, entered_password: str) -> bool:
    """Verify if entered password matches the stored hash. Uses PBKDF2-SHA256 for password hashing."""
    parts = stored_hash.split("$")
    if len(parts) != 3:
        return False

    salt, iterations_str, stored_hash_hex = parts

    # Validate iterations is a valid integer
    if not iterations_str.isdigit():
        return False

    iterations = int(iterations_str)

    # Hash the entered password with the same salt
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        entered_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )

    # Compare hashes using time constant comparison to prevent timing attacks
    return hmac.compare_digest(hashed.hex(), stored_hash_hex)


def authenticate_user(cursor, username: str, password: str) -> bool:
    """Authenticate user by checking username and password."""
    user = get_user_by_username(cursor, username)

    if user is None:
        return False

    return verify_password(user["password_hash"], password)


def generate_password_hash(password: str, iterations: int = 100000) -> str:
    """Generate a password hash using PBKDF2-SHA256."""
    if not password:
        raise ValueError("Password cannot be empty")

    # Generate a random salt
    salt = secrets.token_hex(16)

    # Hash the password
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )

    # Return formatted hash
    return f"{salt}${iterations}${hashed.hex()}"


def validate_signup_input(email: str, password: str) -> bool:
    """Validate signup input: email format and password length."""
    if not email or not password:
        return False

    # Validate email format (basic check)
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return False

    # Validate password length
    if len(password) <= 8:
        return False

    return True


def create_user(cursor, email: str, password_hash: str) -> bool:
    """Insert a new user into the database."""
    try:
        query = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        cursor.execute(query, (email, password_hash))
        cursor.connection.commit()
        return True
    except psycopg2.IntegrityError:
        # Email already exists
        cursor.connection.rollback()
        return False
    except psycopg2.Error as e:
        logger.error(f"Database error creating user: {e}")
        cursor.connection.rollback()
        return False


@st.cache_resource
def get_db_connection_cleanup():
    """Register cleanup for database connection on app exit."""
    def close_conn():
        conn = get_db_connection()
        if conn:
            conn.close()
            logger.info("Database connection closed.")
    return close_conn


# Register cleanup
_cleanup = get_db_connection_cleanup()


# ============== Keyword Management Functions ==============

def add_user_keyword(cursor, user_id: int, keyword: str) -> bool:
    """Add a keyword to a user's tracked keywords."""
    # Insert keyword into keywords table (case-insensitive, do nothing on conflict)
    cursor.execute(
        "INSERT INTO keywords (keyword_value) VALUES (LOWER(%s)) ON CONFLICT (keyword_value) DO NOTHING",
        (keyword,)
    )

    # Add entry to user_keywords table mapping user to keyword
    cursor.execute(
        "INSERT INTO user_keywords (user_id, keyword_id) SELECT %s, keyword_id FROM keywords WHERE LOWER(keyword_value) = LOWER(%s)",
        (user_id, keyword)
    )
    cursor.connection.commit()
    return True


def remove_user_keyword(cursor, user_id: int, keyword: str) -> bool:
    """Remove a keyword from a user's tracked keywords."""
    cursor.execute(
        "DELETE FROM user_keywords WHERE user_id = %s AND keyword_id IN (SELECT keyword_id FROM keywords WHERE LOWER(keyword_value) = LOWER(%s))",
        (user_id, keyword)
    )
    cursor.connection.commit()
    return True


def get_user_keywords(cursor, user_id: int) -> list:
    """Retrieve all keywords for a user."""
    cursor.execute(
        "SELECT k.keyword_value FROM keywords k JOIN user_keywords uk ON k.keyword_id = uk.keyword_id WHERE uk.user_id = %s ORDER BY k.keyword_value",
        (user_id,)
    )
    results = cursor.fetchall()
    return [row["keyword_value"] for row in results] if results else []


# ============== Page Configuration ==============
st.set_page_config(
    page_title="Trends Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Session State Initialization ==============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "keywords" not in st.session_state:
    st.session_state.keywords = ["matcha", "boba", "coffee"]
if "alerts_enabled" not in st.session_state:
    st.session_state.alerts_enabled = False
if "alert_email" not in st.session_state:
    st.session_state.alert_email = ""


# ============== Placeholder Data Generators ==============
def generate_placeholder_metrics(keyword: str, days: int) -> dict:
    """Generate placeholder KPI metrics for a keyword."""
    random.seed(hash(keyword) + days)
    return {
        "mentions": random.randint(500, 5000),
        "posts": random.randint(200, 2000),
        "reposts": random.randint(100, 1500),
        "comments": random.randint(150, 1800),
        "avg_sentiment": round(random.uniform(-0.3, 0.7), 2)
    }


def generate_time_series_data(keyword: str, days: int) -> pd.DataFrame:
    """Generate placeholder time series data for activity metrics."""
    random.seed(hash(keyword))
    dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]
    data = {
        "date": dates,
        "posts": [random.randint(10, 100) for _ in dates],
        "reposts": [random.randint(5, 80) for _ in dates],
        "comments": [random.randint(8, 90) for _ in dates],
    }
    return pd.DataFrame(data)


def generate_sentiment_breakdown(keyword: str) -> dict:
    """Generate placeholder sentiment distribution."""
    random.seed(hash(keyword))
    positive = random.randint(30, 50)
    negative = random.randint(10, 30)
    neutral = 100 - positive - negative
    return {"Positive": positive, "Neutral": neutral, "Negative": negative}


def generate_keywords_summary(keywords: list, days: int) -> pd.DataFrame:
    """Generate summary table for all keywords."""
    data = []
    for kw in keywords:
        metrics = generate_placeholder_metrics(kw, days)
        data.append({
            "Keyword": kw,
            "Mentions": metrics["mentions"],
            "Posts": metrics["posts"],
            "Reposts": metrics["reposts"],
            "Comments": metrics["comments"],
            "Avg Sentiment": metrics["avg_sentiment"]
        })
    return pd.DataFrame(data)


def generate_llm_summary(keyword: str, days: int) -> str:
    """Generate placeholder LLM summary."""
    return f"""
    **📝 AI Summary for "{keyword}" (Last {days} days)**

    The topic "{keyword}" has shown moderate engagement over the selected period.
    Overall sentiment appears to be leaning positive with a notable increase in mentions
    during peak hours. Key themes include product reviews, lifestyle content, and
    community discussions. Consider monitoring related trending terms for broader insights.

    *[This is a placeholder summary - will be generated by LLM integration]*
    """


# ============== Login Page ==============
def show_login_page():
    """Display the login/signup page."""
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
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            cursor.close()
                            st.error("Email already exists. Please use a different email.")
                    else:
                        st.error("Unable to connect to database. Please try again later.")


# ============== Main Analytics Dashboard ==============
def show_analytics_dashboard():
    """Display the main analytics dashboard."""
    st.title("📊 Analytics Dashboard")

    # Top controls row
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        selected_keyword = st.selectbox(
            "Select Keyword",
            options=st.session_state.keywords,
            index=0
        )
    with col2:
        days_options = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}
        selected_period = st.selectbox("Time Period", options=list(days_options.keys()))
        days = days_options[selected_period]

    st.markdown("---")

    # LLM Summary Section
    st.markdown(generate_llm_summary(selected_keyword, days))

    st.markdown("---")

    # KPI Metrics Row
    metrics = generate_placeholder_metrics(selected_keyword, days)

    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    with kpi_col1:
        st.metric(
            label="📢 Mentions",
            value=f"{metrics['mentions']:,}",
            delta=f"{random.randint(-10, 20)}%"
        )
    with kpi_col2:
        st.metric(
            label="📝 Posts",
            value=f"{metrics['posts']:,}",
            delta=f"{random.randint(-10, 20)}%"
        )
    with kpi_col3:
        st.metric(
            label="🔄 Reposts",
            value=f"{metrics['reposts']:,}",
            delta=f"{random.randint(-10, 20)}%"
        )
    with kpi_col4:
        st.metric(
            label="💬 Comments",
            value=f"{metrics['comments']:,}",
            delta=f"{random.randint(-10, 20)}%"
        )
    with kpi_col5:
        sentiment_color = "normal" if metrics['avg_sentiment'] >= 0 else "inverse"
        st.metric(
            label="😊 Avg Sentiment",
            value=f"{metrics['avg_sentiment']:.2f}",
            delta=f"{random.uniform(-0.1, 0.1):.2f}",
            delta_color=sentiment_color
        )

    st.markdown("---")

    # Charts Row 1: Activity Over Time & Sentiment Breakdown
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📈 Activity Metrics Over Time")
        time_data = generate_time_series_data(selected_keyword, days)

        # Melt data for Altair multi-line chart
        time_data_melted = time_data.melt(
            id_vars=["date"],
            value_vars=["posts", "reposts", "comments"],
            var_name="Metric",
            value_name="Count"
        )

        line_chart = alt.Chart(time_data_melted).mark_line(point=True).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("Count:Q", title="Count"),
            color=alt.Color("Metric:N", scale=alt.Scale(
                domain=["posts", "reposts", "comments"],
                range=["#636EFA", "#EF553B", "#00CC96"]
            )),
            tooltip=["date:T", "Metric:N", "Count:Q"]
        ).properties(height=350).interactive()

        st.altair_chart(line_chart, use_container_width=True)

    with chart_col2:
        st.markdown("### 🎭 Sentiment Breakdown")
        sentiment_data = generate_sentiment_breakdown(selected_keyword)

        sentiment_df = pd.DataFrame({
            "Sentiment": list(sentiment_data.keys()),
            "Percentage": list(sentiment_data.values())
        })

        pie_chart = alt.Chart(sentiment_df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("Percentage:Q"),
            color=alt.Color("Sentiment:N", scale=alt.Scale(
                domain=["Positive", "Neutral", "Negative"],
                range=["#00CC96", "#636EFA", "#EF553B"]
            )),
            tooltip=["Sentiment:N", "Percentage:Q"]
        ).properties(height=350)

        st.altair_chart(pie_chart, use_container_width=True)

    st.markdown("---")

    # Charts Row 2: Overall Sentiment & Daily Averages
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("### 📊 Overall Sentiment Score Over Time")
        time_data["sentiment"] = [round(random.uniform(-0.5, 0.8), 2) for _ in range(len(time_data))]

        # Area chart with sentiment
        sentiment_area = alt.Chart(time_data).mark_area(
            line={"color": "#AB63FA"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="white", offset=0),
                    alt.GradientStop(color="#AB63FA", offset=1)
                ],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("sentiment:Q", title="Sentiment Score", scale=alt.Scale(domain=[-1, 1])),
            tooltip=["date:T", "sentiment:Q"]
        ).properties(height=300)

        # Add horizontal line at y=0
        zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            strokeDash=[5, 5], color="gray"
        ).encode(y="y:Q")

        st.altair_chart(sentiment_area + zero_line, use_container_width=True)

    with chart_col4:
        st.markdown("### 📅 Daily Average by Metric Type")
        avg_data = pd.DataFrame({
            "Metric": ["Posts", "Reposts", "Comments"],
            "Daily Avg": [
                round(time_data["posts"].mean(), 1),
                round(time_data["reposts"].mean(), 1),
                round(time_data["comments"].mean(), 1)
            ]
        })

        bar_chart = alt.Chart(avg_data).mark_bar().encode(
            x=alt.X("Metric:N", title="Metric"),
            y=alt.Y("Daily Avg:Q", title="Daily Average"),
            color=alt.Color("Metric:N", scale=alt.Scale(
                domain=["Posts", "Reposts", "Comments"],
                range=["#636EFA", "#EF553B", "#00CC96"]
            ), legend=None),
            tooltip=["Metric:N", "Daily Avg:Q"]
        ).properties(height=300)

        st.altair_chart(bar_chart, use_container_width=True)

    st.markdown("---")

    # Chart Row 3: Keyword Comparison
    st.markdown("### 🔍 Keyword Mentions Comparison")
    if len(st.session_state.keywords) > 0:
        comparison_data = pd.DataFrame({
            "Keyword": st.session_state.keywords,
            "Mentions": [generate_placeholder_metrics(kw, days)["mentions"] for kw in st.session_state.keywords]
        })

        comparison_chart = alt.Chart(comparison_data).mark_bar().encode(
            x=alt.X("Keyword:N", title="Keyword"),
            y=alt.Y("Mentions:Q", title="Mentions"),
            color=alt.Color("Keyword:N", scale=alt.Scale(scheme="set2"), legend=None),
            tooltip=["Keyword:N", "Mentions:Q"]
        ).properties(height=300)

        st.altair_chart(comparison_chart, use_container_width=True)
    else:
        st.info("Add keywords in the Topics tab to see comparison data.")

    st.markdown("---")

    # Summary Table
    st.markdown("### 📋 Keywords Summary Table")
    if len(st.session_state.keywords) > 0:
        summary_df = generate_keywords_summary(st.session_state.keywords, days)

        # Style the dataframe
        def color_sentiment(val):
            if val > 0.2:
                return "background-color: #d4edda"
            elif val < -0.2:
                return "background-color: #f8d7da"
            return ""

        styled_df = summary_df.style.applymap(
            color_sentiment, subset=["Avg Sentiment"]
        ).format({"Avg Sentiment": "{:.2f}"})

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("Add keywords in the Topics tab to see summary data.")


# ============== Topics Dashboard ==============
def show_topics_dashboard():
    """Display the topics/keywords management dashboard."""
    st.title("🏷️ Topics Management")
    st.markdown("Manage your tracked keywords and topics here.")

    st.markdown("---")

    # Load keywords from database on first visit
    if "keywords_loaded" not in st.session_state:
        conn = get_db_connection()
        if conn and st.session_state.user_id:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords
            st.session_state.keywords_loaded = True

    # Add new keyword section
    st.markdown("### ➕ Add New Keyword")
    col1, col2 = st.columns([3, 1])

    with col1:
        new_keyword = st.text_input(
            "Enter keyword",
            placeholder="e.g., matcha, tea, boba...",
            label_visibility="collapsed"
        )
    with col2:
        if st.button("Add Keyword", type="primary", use_container_width=True):
            if new_keyword:
                if new_keyword.lower() not in [k.lower() for k in st.session_state.keywords]:
                    # Add to database
                    conn = get_db_connection()
                    if conn and st.session_state.user_id:
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        add_user_keyword(cursor, st.session_state.user_id, new_keyword)
                        cursor.close()

                    # Add to session state
                    st.session_state.keywords.append(new_keyword.lower())
                    st.success(f'Added "{new_keyword}" to your keywords!')
                    st.rerun()
                else:
                    st.warning("This keyword already exists.")
            else:
                st.error("Please enter a keyword.")

    st.markdown("---")

    # Current keywords display
    st.markdown("### 📝 Your Keywords")

    if len(st.session_state.keywords) > 0:
        # Display keywords as a grid with delete buttons
        cols = st.columns(4)
        for idx, keyword in enumerate(st.session_state.keywords):
            with cols[idx % 4]:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"""
                    <div style="
                        background-color: #f0f2f6;
                        padding: 10px 15px;
                        border-radius: 20px;
                        margin: 5px 0;
                        text-align: center;
                        font-weight: 500;
                    ">
                        {keyword}
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    if st.button("🗑️", key=f"delete_{idx}"):
                        # Remove from database
                        conn = get_db_connection()
                        if conn and st.session_state.user_id:
                            cursor = conn.cursor(cursor_factory=RealDictCursor)
                            remove_user_keyword(cursor, st.session_state.user_id, keyword)
                            cursor.close()

                        # Remove from session state
                        st.session_state.keywords.remove(keyword)
                        st.rerun()

        st.markdown("---")

# ============== Alerts Dashboard ==============
def show_alerts_dashboard():
    """Display the alerts/notifications management dashboard."""
    st.title("🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")

    st.markdown("---")

    # Email alerts section
    st.markdown("### 📧 Email Alerts")

    alerts_enabled = st.toggle(
        "Enable Email Alerts",
        value=st.session_state.alerts_enabled,
        help="Receive email notifications for significant trend changes"
    )
    st.session_state.alerts_enabled = alerts_enabled

    if alerts_enabled:
        col1, col2 = st.columns([3, 1])
        with col1:
            alert_email = st.text_input(
                "Email Address",
                value=st.session_state.alert_email,
                placeholder="your@email.com"
            )
        with col2:
            if st.button("Save Email", type="primary", use_container_width=True):
                if alert_email and "@" in alert_email:
                    st.session_state.alert_email = alert_email
                    st.success("Email saved successfully!")
                else:
                    st.error("Please enter a valid email address.")

        st.markdown("---")

        # Alert preferences
        st.markdown("### ⚙️ Alert Preferences")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Trigger Alerts When:**")
            st.checkbox("Mentions increase by more than 50%", value=True)
            st.checkbox("Sentiment drops below -0.3", value=True)
            st.checkbox("New trending keyword detected", value=False)
            st.checkbox("Daily summary report", value=True)

        with col2:
            st.markdown("**Alert Frequency:**")
            st.radio(
                "How often should we send alerts?",
                options=["Immediately", "Hourly digest", "Daily digest"],
                index=0,
                label_visibility="collapsed"
            )

        st.markdown("---")

        # Keywords to monitor
        st.markdown("### 🏷️ Keywords to Monitor")
        st.markdown("Select which keywords should trigger alerts:")

        if len(st.session_state.keywords) > 0:
            monitored_keywords = []
            cols = st.columns(4)
            for idx, keyword in enumerate(st.session_state.keywords):
                with cols[idx % 4]:
                    if st.checkbox(keyword, value=True, key=f"monitor_{keyword}"):
                        monitored_keywords.append(keyword)

            st.info(f"Monitoring {len(monitored_keywords)} of {len(st.session_state.keywords)} keywords")
        else:
            st.warning("No keywords to monitor. Add keywords in the Topics tab first.")

    else:
        st.info("Enable email alerts above to configure notification settings.")

    st.markdown("---")

    # Alert history placeholder
    st.markdown("### 📜 Recent Alerts")
    st.markdown("*Alert history will be displayed here when connected to the database.*")

    # Placeholder alert history
    placeholder_alerts = pd.DataFrame({
        "Date": ["2026-02-03", "2026-02-02", "2026-02-01"],
        "Type": ["Mention Spike", "Sentiment Drop", "Daily Summary"],
        "Keyword": ["matcha", "boba", "All"],
        "Status": ["Sent", "Sent", "Sent"]
    })
    st.dataframe(placeholder_alerts, use_container_width=True, hide_index=True)


# ============== Sidebar Navigation ==============
def show_sidebar():
    """Display the sidebar navigation."""
    with st.sidebar:
        st.markdown(f"### 👋 Hello, {st.session_state.username}!")
        st.markdown("---")

        # Navigation
        st.markdown("### 🧭 Navigation")
        page = st.radio(
            "Go to",
            options=["📊 Analytics", "🏷️ Topics", "🔔 Alerts"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Quick stats
        st.markdown("### 📈 Quick Stats")
        st.metric("Keywords Tracked", len(st.session_state.keywords))
        st.metric("Alerts Enabled", "Yes" if st.session_state.alerts_enabled else "No")

        st.markdown("---")

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_id = None
            st.rerun()

        st.markdown("---")
        st.caption("Trends Tracker v1.0 (Mockup)")

    return page


# ============== Main App ==============
def main():
    """Main application entry point."""
    if not st.session_state.logged_in:
        show_login_page()
    else:
        page = show_sidebar()

        if page == "📊 Analytics":
            show_analytics_dashboard()
        elif page == "🏷️ Topics":
            show_topics_dashboard()
        elif page == "🔔 Alerts":
            show_alerts_dashboard()


if __name__ == "__main__":
    main()

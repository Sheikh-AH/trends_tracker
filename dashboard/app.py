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


# ============== Visualization Data Generators ==============

def generate_word_cloud_data(keyword: str, days: int) -> dict:
    """Generate word frequency data for word cloud visualization."""
    random.seed(hash(keyword) + days)

    # Associated words vary by keyword
    word_pools = {
        "matcha": ["latte", "green", "tea", "healthy", "cafe", "japanese", "powder", "organic", "iced", "oat"],
        "boba": ["milk", "tea", "tapioca", "pearls", "sweet", "bubble", "drink", "asian", "chewy", "sugar"],
        "coffee": ["espresso", "latte", "beans", "morning", "caffeine", "roast", "brew", "americano", "mocha", "cold"],
    }

    # Use keyword-specific words or generic ones
    base_words = word_pools.get(keyword.lower(), [
        "trending", "popular", "viral", "discussed", "mentioned", "shared", "liked", "commented", "posted", "engaged"
    ])

    # Add some common words
    common_words = ["love", "great", "best", "new", "try", "amazing", "delicious", "perfect", "favorite", "recommend"]
    all_words = base_words + common_words

    # Generate frequencies
    return {word: random.randint(10, 100) for word in all_words}


def generate_sentiment_calendar_data(keyword: str, days: int) -> pd.DataFrame:
    """Generate daily sentiment data for calendar heatmap visualization."""
    random.seed(hash(keyword) + days)

    dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]

    data = []
    for date in dates:
        sentiment = round(random.uniform(-0.5, 0.8), 2)
        data.append({
            "date": date,
            "sentiment": sentiment,
            "day_of_week": date.weekday(),
            "week": date.isocalendar()[1]
        })

    return pd.DataFrame(data)


def generate_trending_velocity(keyword: str, days: int) -> dict:
    """Generate trending velocity data for speedometer visualization."""
    random.seed(hash(keyword) + days)

    velocity = random.randint(20, 85)
    percent_change = round(random.uniform(-30, 50), 1)

    if percent_change > 10:
        direction = "accelerating"
    elif percent_change < -10:
        direction = "decelerating"
    else:
        direction = "stable"

    return {
        "velocity": velocity,
        "direction": direction,
        "percent_change": percent_change,
        "current_mentions": random.randint(500, 3000),
        "previous_mentions": random.randint(400, 2500)
    }


def generate_network_graph_data(keywords: list) -> dict:
    """Generate node and edge data for keyword network graph visualization."""
    if not keywords:
        return {"nodes": [], "edges": []}

    random.seed(hash(tuple(keywords)))

    # Create nodes for each keyword
    nodes = [{"id": kw, "label": kw, "size": random.randint(20, 50)} for kw in keywords]

    # Add related topic nodes
    related_topics = {
        "matcha": ["latte", "green tea", "healthy"],
        "boba": ["milk tea", "tapioca", "asian drinks"],
        "coffee": ["espresso", "caffeine", "morning"]
    }

    for kw in keywords:
        topics = related_topics.get(kw.lower(), ["topic1", "topic2"])
        for topic in topics[:2]:  # Limit to 2 related topics per keyword
            nodes.append({"id": topic, "label": topic, "size": random.randint(10, 30)})

    # Create edges between keywords and their related topics
    edges = []
    for kw in keywords:
        topics = related_topics.get(kw.lower(), ["topic1", "topic2"])
        for topic in topics[:2]:
            edges.append({
                "source": kw,
                "target": topic,
                "weight": random.randint(5, 30)
            })

    # Add edges between keywords that co-occur
    for i, kw1 in enumerate(keywords):
        for kw2 in keywords[i+1:]:
            if random.random() > 0.5:  # 50% chance of connection
                edges.append({
                    "source": kw1,
                    "target": kw2,
                    "weight": random.randint(10, 40)
                })

    return {"nodes": nodes, "edges": edges}


def generate_random_post(keyword: str) -> dict:
    """Generate a random post for typing animation display."""
    random.seed(hash(keyword) + int(datetime.now().timestamp() // 60))  # Changes every minute

    post_templates = [
        f"Just discovered the best {keyword} spot in town! Highly recommend 🙌",
        f"Anyone else obsessed with {keyword} lately? Can't get enough!",
        f"Hot take: {keyword} is overrated. Change my mind 🤔",
        f"My morning routine isn't complete without {keyword} ☀️",
        f"Tried a new {keyword} recipe today and it was amazing!",
        f"The {keyword} trend is everywhere and I'm here for it 💯",
        f"Unpopular opinion: {keyword} hits different at night",
        f"Finally found a place that does {keyword} right! 🎯",
    ]

    authors = ["@trendwatcher", "@foodie_life", "@daily_vibes", "@lifestyle_guru", "@taste_explorer"]

    return {
        "text": random.choice(post_templates),
        "author": random.choice(authors),
        "timestamp": datetime.now() - timedelta(hours=random.randint(1, 48)),
        "likes": random.randint(50, 500),
        "reposts": random.randint(10, 100)
    }


def generate_ai_insights(keyword: str, days: int) -> dict:
    """Generate AI-powered insights for a keyword."""
    random.seed(hash(keyword) + days)

    themes = [
        "Product reviews and recommendations",
        "Lifestyle and wellness content",
        "Community discussions",
        "Recipe sharing",
        "Price comparisons"
    ]

    positive_drivers = [
        "High-quality product mentions",
        "Positive customer experiences",
        "Influencer endorsements"
    ]

    negative_drivers = [
        "Price concerns",
        "Availability issues",
        "Quality inconsistencies"
    ]

    recommendations = [
        f"Monitor '{keyword} alternatives' - emerging search term",
        f"Peak engagement for {keyword} occurs between 9-11 AM",
        f"Consider tracking related hashtags for broader reach",
        f"Sentiment dips on weekends - investigate weekend-specific concerns"
    ]

    summary = f"""The topic "{keyword}" has shown {'strong' if random.random() > 0.5 else 'moderate'} engagement over the last {days} days. Overall sentiment is {'predominantly positive' if random.random() > 0.4 else 'mixed'}, with notable spikes during {'morning' if random.random() > 0.5 else 'evening'} hours. Key discussions center around product quality and lifestyle integration. {'An emerging trend shows increased interest in premium variants.' if random.random() > 0.5 else 'Community-driven content is gaining traction.'}"""

    return {
        "summary": summary,
        "themes": random.sample(themes, k=3),
        "sentiment_drivers": {
            "positive": random.sample(positive_drivers, k=2),
            "negative": random.sample(negative_drivers, k=2)
        },
        "recommendations": random.sample(recommendations, k=3)
    }


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


# ============== Main App ==============
def main():
    """Main application entry point."""
    if not st.session_state.logged_in:
        show_login_page()
    else:
        # Redirect to Home page after login
        st.switch_page("pages/1_Home.py")


if __name__ == "__main__":
    main()


"""
Utility functions for Trends Tracker Dashboard.
Shared functions for database, authentication, keyword management, and data generation.
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import streamlit as st
from datetime import datetime, timedelta
from os import environ as ENV
from typing import Optional
import random

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import streamlit as st
from dotenv import load_dotenv

# ============== Logging Configuration ==============
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


# ============== Database Functions ==============
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


@st.cache_resource
def get_db_connection_cleanup():
    """Register cleanup for database connection on app exit."""
    def close_conn():
        conn = get_db_connection()
        if conn:
            conn.close()
            logger.info("Database connection closed.")
    return close_conn


# ============== Authentication Functions ==============
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
        st.error("Email already exists. Please use a different email.")
        return False
    except psycopg2.Error as e:
        logger.error(f"Database error creating user: {e}")
        st.error("Database error occurred. Please try again later.")
        cursor.connection.rollback()
        return False


# ============== Keyword Management Functions ==============
def get_user_keywords(cursor, user_id: int) -> list:
    """Retrieve all keywords for a user."""
    cursor.execute(
        "SELECT k.keyword_value FROM keywords k JOIN user_keywords uk ON k.keyword_id = uk.keyword_id WHERE uk.user_id = %s ORDER BY k.keyword_value",
        (user_id,)
    )
    results = cursor.fetchall()
    return [row["keyword_value"] for row in results] if results else []


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


# ============== Database Query Functions ==============
def _load_sql_query(filename: str) -> str:
    """Load SQL query from queries folder."""
    query_path = os.path.join(os.path.dirname(__file__), "queries", filename)
    with open(query_path, "r") as f:
        return f.read()


def calc_delta(current: float, baseline: float) -> float:
    """
    Calculate percentage change from baseline.
    If baseline is 0 (no prior data), returns 0.0
    """
    if baseline == 0:
        return 0.0
    return round(((current - baseline) / baseline) * 100, 1)


def get_kpi_metrics_from_db(conn: psycopg2.extensions.connection, keyword: str, days: int) -> dict:
    """
    Fetch KPI metrics from database for a given keyword and time period.
    Calculates deltas by comparing current period to baseline (N days ago).
    If no baseline data exists, delta is set to 0.
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now()
    current_start = now - timedelta(days=days)
    baseline_start = current_start - timedelta(days=days)
    keyword_lower = keyword.lower()

    try:
        # Load and execute mention count query
        mention_query = _load_sql_query("get_mention_count.sql")
        cursor.execute(mention_query, (
            current_start,                  # current period start (now - days)
            baseline_start,                 # baseline period start (now - days*2)
            current_start,                  # baseline period end (now - days)
            keyword_lower,                  # keyword filter
            baseline_start                  # overall filter (now - days*2)
        ))
        mention_result = cursor.fetchone()
        if mention_result:
            current_mentions = mention_result.get("current_mentions") or 0
            baseline_mentions = mention_result.get("baseline_mentions") or 0
        else:
            current_mentions = 0
            baseline_mentions = 0

        # Load and execute KPI metrics query
        kpi_query = _load_sql_query("get_kpi_metrics.sql")
        cursor.execute(kpi_query, (
            current_start,                  # current_posts
            baseline_start,                 # baseline_posts start
            current_start,                  # baseline_posts end
            current_start,                  # current_reposts
            baseline_start,                 # baseline_reposts start
            current_start,                  # baseline_reposts end
            current_start,                  # current_comments
            baseline_start,                 # baseline_comments start
            current_start,                  # baseline_comments end
            current_start,                  # current_sentiment
            baseline_start,                 # baseline_sentiment start
            current_start,                  # baseline_sentiment end
            keyword_lower,                  # keyword filter
            baseline_start                  # overall filter (now - days*2)
        ))

        result = cursor.fetchone()
        if result:
            current_posts = result.get("current_posts") or 0
            baseline_posts = result.get("baseline_posts") or 0
            current_reposts = result.get("current_reposts") or 0
            baseline_reposts = result.get("baseline_reposts") or 0
            current_comments = result.get("current_comments") or 0
            baseline_comments = result.get("baseline_comments") or 0
            current_sentiment = round(result.get("current_sentiment") or 0, 2)
            baseline_sentiment = round(result.get("baseline_sentiment") or 0, 2)
        else:
            current_posts = 0
            baseline_posts = 0
            current_reposts = 0
            baseline_reposts = 0
            current_comments = 0
            baseline_comments = 0
            current_sentiment = 0.0
            baseline_sentiment = 0.0

        return {
            "mentions": current_mentions,
            "posts": current_posts,
            "reposts": current_reposts,
            "comments": current_comments,
            "avg_sentiment": current_sentiment,
            "mentions_delta": calc_delta(current_mentions, baseline_mentions),
            "posts_delta": calc_delta(current_posts, baseline_posts),
            "reposts_delta": calc_delta(current_reposts, baseline_reposts),
            "comments_delta": calc_delta(current_comments, baseline_comments),
            "sentiment_delta": current_sentiment - baseline_sentiment
        }

    except Exception as e:
        logger.error(f"Error fetching KPI metrics: {e}")
        print(f"ERROR in get_kpi_metrics_from_db: {e}")

    finally:
        cursor.close()


# ============== Placeholder Data Generators ==============
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


# ============== Featured Posts Functions ==============
def get_sentiment_by_day(conn, keyword: str, day_limit: int = 31) -> list[dict]:
    """Get average sentiment per day for a keyword over the specified period."""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = _load_sql_query("get_sentiment_by_day.sql")
        cursor.execute(query, (keyword, day_limit))
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results] if results else []
    except Exception as e:
        logger.error(f"Error fetching sentiment by day: {e}")
        return []


def get_posts_by_date(conn, keyword: str, date, limit: int = 10) -> list[dict]:
    """Get random posts for a specific date and keyword."""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = _load_sql_query("get_posts_by_date.sql")
        cursor.execute(query, (keyword, date, limit))
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results] if results else []
    except Exception as e:
        logger.error(f"Error fetching posts by date: {e}")
        return []


def get_latest_post_text_corpus(
    conn,
    keyword_value: str,
    day_limit: int = 7,
    post_count_limit: int = 10000
) -> str:
    """
    Extract post texts from the last N days for a keyword as a single corpus.

    Args:
        conn: Database connection object
        keyword_value: Keyword to filter posts by
        day_limit: Number of days to look back (default 7)
        post_count_limit: Maximum number of posts to retrieve (default 10000)

    Returns:
        Single string containing all post texts concatenated with newlines
    """
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = _load_sql_query("get_latest_post_text_corpus.sql")
        cursor.execute(query, (keyword_value, day_limit, post_count_limit))
        results = cursor.fetchall()
        cursor.close()

        if not results:
            return ""

        # Concatenate all post texts into a single corpus
        corpus = "\n".join(row["text"] for row in results if row.get("text"))
        return corpus
    except Exception as e:
        logger.error(f"Error fetching post text corpus: {e}")
        return ""


def get_most_recent_bluesky_posts(cursor, keyword: str, limit: int = 10) -> list:
    """Retrieve the most recent posts from bluesky_posts table matching a keyword."""
    try:
        query = _load_sql_query("get_most_recent_bluesky_posts.sql")
        cursor.execute(query, (keyword, limit))
        results = cursor.fetchall()
        return [dict(row) for row in results] if results else []
    except Exception as e:
        logger.error(f"Error fetching recent posts: {e}")
        return []


def uri_to_url(post_uri: str) -> str:
    """Convert a Bluesky post URI to a shareable HTTPS URL."""
    if not post_uri or not isinstance(post_uri, str):
        return ""

    try:
        # Format: at://did:plc:xxx/app.bsky.feed.post/rkey
        if not post_uri.startswith("at://"):
            return ""

        # Remove "at://" prefix and split
        uri_without_prefix = post_uri[5:]
        parts = uri_without_prefix.split("/")

        if len(parts) < 2:
            return ""

        # Extract DID (first part) and rkey (last part)
        did = parts[0]
        rkey = parts[-1]

        return f"https://bsky.app/profile/{did}/post/{rkey}"

    except Exception as e:
        logger.error(f"Error converting URI to URL: {e}")
        return ""


def get_handle_from_did(did: str) -> Optional[str]:
    """Retrieve a Bluesky handle from a DID using the Bluesky API."""
    if not did or not isinstance(did, str):
        return None

    try:
        url = f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={did}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            handle = data.get("handle")
            return f"@{handle}" if handle else None
        return None
    except requests.RequestException as e:
        logger.error(f"Error fetching handle for DID {did}: {e}")
        return None


def get_post_engagement(post_uri: str) -> dict:
    """Fetch engagement metrics (likes, reposts, comments) for a post."""
    if not post_uri or not isinstance(post_uri, str):
        return {"likes": 0, "reposts": 0, "comments": 0}

    try:
        # Parse post_uri to extract author DID and rkey
        # Format: at://did:plc:xxx/app.bsky.feed.post/rkey
        parts = post_uri.split("/")
        if len(parts) < 5:
            return {"likes": 0, "reposts": 0, "comments": 0}

        # Use getPostThread to get engagement metrics
        url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri={post_uri}&depth=0"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            thread = data.get("thread", {})
            post = thread.get("post", {})

            return {
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "comments": post.get("replyCount", 0)
            }
        return {"likes": 0, "reposts": 0, "comments": 0}
    except requests.RequestException as e:
        logger.error(f"Error fetching engagement for post {post_uri}: {e}")
        return {"likes": 0, "reposts": 0, "comments": 0}


def get_featured_posts(cursor, keyword: str, limit: int = 10) -> list[dict]:
    """Get featured posts matching a keyword with full metadata."""
    posts = get_most_recent_bluesky_posts(cursor, keyword, limit)

    featured = []
    for post in posts:
        author_did = post.get("author_did", "")
        post_uri = post.get("post_uri", "")

        # Get author handle
        handle = get_handle_from_did(author_did)
        if not handle:
            handle = f"@{author_did[:20]}..." if author_did else "@unknown"

        # Get engagement metrics
        engagement = get_post_engagement(post_uri)

        # Convert URI to URL
        post_url = uri_to_url(post_uri)

        # Derive author URL from author DID
        author_url = f"https://bsky.app/profile/{author_did}" if author_did else ""

        featured.append({
            "post_text": post.get("text", ""),
            "author": handle,
            "timestamp": post.get("posted_at", datetime.now()),
            "likes": engagement.get("likes", 0),
            "reposts": engagement.get("reposts", 0),
            "comments": engagement.get("comments", 0),
            "post_uri": post_uri,
            "post_url": post_url,
            "author_url": author_url
        })

    return featured

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


# ============== UI Functions ==============
def render_sidebar():
    """Render the standard sidebar across all pages."""
    with st.sidebar:
        st.markdown(f"### 👋 Hello, {st.session_state.get('username', 'User')}!")
        st.markdown("---")
        st.markdown("### 📈 Quick Stats")
        st.metric("Keywords Tracked", len(st.session_state.get("keywords", [])))
        st.metric("Email Reports Enabled", "Yes" if st.session_state.get("emails_enabled", False) else "No")
        st.metric("Alerts Enabled", "Yes" if st.session_state.get("alerts_enabled", False) else "No")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_id = None
            st.switch_page("app.py")
        st.markdown("---")
        st.caption("Trends Tracker v1.0")


# ============== Sentiment Functions ==============
def get_sentiment_emoji(sentiment_score: float) -> str:
    """Get emoji based on sentiment score with gradient smileys."""
    if sentiment_score >= 0.4:
        return "😄"  # Grinning
    elif sentiment_score >= 0.25:
        return "😊"  # Smiling
    elif sentiment_score >= 0.1:
        return "🙂"  # Slightly smiling
    elif sentiment_score >= -0.1:
        return "😐"  # Neutral
    elif sentiment_score >= -0.25:
        return "😕"  # Slightly frowning
    elif sentiment_score >= -0.4:
        return "😔"  # Frowning
    else:
        return "😠"  # Angry


# ============== Keyword Extraction Functions ==============
def extract_keywords_yake(
    text_corpus: str,
    language: str = "en",
    max_ngram_size: int = 2,
    deduplication_threshold: float = 0.5,
    num_keywords: int = 50
) -> list[dict]:
    """Extract keywords from text corpus using YAKE."""
    import yake

    if not text_corpus or not text_corpus.strip():
        return []

    kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=max_ngram_size,
        dedupLim=deduplication_threshold,
        top=num_keywords,
        features=None
    )

    keywords = kw_extractor.extract_keywords(text_corpus)

    return [
        {"keyword": kw, "score": score}
        for kw, score in keywords
    ]


def diversify_keywords(
    keywords: list[dict],
    search_term: str,
    max_results: int = 30
) -> list[dict]:
    """Post-process keywords to increase diversity by filtering redundant terms."""
    if not keywords:
        return []

    # Normalize search term words
    search_words = set(search_term.lower().split())

    diversified = []
    seen_word_sets = []

    for kw in keywords:
        kw_lower = kw["keyword"].lower()
        kw_words = set(kw_lower.split())

        # Skip if keyword contains search term words
        if search_words & kw_words:
            continue

        # Skip if >50% overlap with any already-selected keyword
        is_redundant = False
        for seen_words in seen_word_sets:
            overlap = len(kw_words & seen_words)
            min_len = min(len(kw_words), len(seen_words))
            if min_len > 0 and overlap / min_len > 0.5:
                is_redundant = True
                break

        if not is_redundant:
            diversified.append(kw)
            seen_word_sets.append(kw_words)

        if len(diversified) >= max_results:
            break

    return diversified


# ============== Data Formatting Functions ==============
def convert_sentiment_score(sentiment_raw) -> float:
    """Convert sentiment score to float, handling various input types."""
    try:
        return float(sentiment_raw) if sentiment_raw is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def format_timestamp(posted_at) -> str:
    """Format timestamp to HH:MM AM/PM or return empty string if invalid."""
    if not posted_at:
        return ''
    if hasattr(posted_at, 'strftime'):
        return posted_at.strftime('%I:%M %p')
    return str(posted_at)


def format_author_display(author_did: str, max_length: int = 20) -> str:
    """Format author DID with @ prefix and truncate if longer than max_length."""
    if len(author_did) > max_length:
        return f"@{author_did[:max_length]}..."
    return f"@{author_did}"


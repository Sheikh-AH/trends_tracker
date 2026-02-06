"""This module fetches all data needed for the weekly email report."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta


def get_db_connection() -> psycopg2.extensions.connection:
    """Establishes and returns a database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def get_all_users(conn: psycopg2.extensions.connection) -> list[dict]:
    """Fetches all users with email alerts enabled."""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT user_id, email
        FROM users
        WHERE send_email = true
    """)

    users = cur.fetchall()
    cur.close()

    return users


def get_user_keywords(conn: psycopg2.extensions.connection, user_id: int) -> list[str]:
    """Fetches all keywords a user is tracking."""
    cur = conn.cursor()

    cur.execute("""
        SELECT k.keyword_value
        FROM keywords k
        JOIN user_keywords uk ON k.keyword_id = uk.keyword_id
        WHERE uk.user_id = %s
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()

    return [row[0] for row in rows]


def get_post_count(conn: psycopg2.extensions.connection, keyword: str, hours: int) -> int:
    """Fetches the count of posts mentioning the keyword in the last N hours."""
    cur = conn.cursor()

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    cur.execute("""
        SELECT COUNT(*) 
        FROM matches m
        JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
        WHERE m.keyword_value = %s
        AND bp.posted_at >= %s
    """, (keyword, cutoff_time))

    count = cur.fetchone()[0]
    cur.close()

    return count


def get_post_count_between(conn: psycopg2.extensions.connection, keyword: str, start_hours_ago: int, end_hours_ago: int) -> int:
    """Fetches post count for a keyword between two time periods (for week-over-week comparison)."""
    cur = conn.cursor()

    start_time = datetime.now(timezone.utc) - timedelta(hours=start_hours_ago)
    end_time = datetime.now(timezone.utc) - timedelta(hours=end_hours_ago)

    cur.execute("""
        SELECT COUNT(*) 
        FROM matches m
        JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
        WHERE m.keyword_value = %s
        AND bp.posted_at >= %s
        AND bp.posted_at < %s
    """, (keyword, start_time, end_time))

    count = cur.fetchone()[0]
    cur.close()

    return count


def get_sentiment_breakdown(conn: psycopg2.extensions.connection, keyword: str, hours: int = 168) -> dict:
    """Fetches sentiment breakdown (positive/neutral/negative) for a keyword over the last N hours (default 7 days).

    Sentiment score ranges:
    - Positive: > 0.1
    - Neutral: -0.1 to 0.1
    - Negative: < -0.1
    """
    cur = conn.cursor()

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    cur.execute("""
        SELECT 
            SUM(CASE WHEN bp.sentiment_score::NUMERIC > 0.1 THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN bp.sentiment_score::NUMERIC >= -0.1 AND bp.sentiment_score::NUMERIC <= 0.1 THEN 1 ELSE 0 END) as neutral,
            SUM(CASE WHEN bp.sentiment_score::NUMERIC < -0.1 THEN 1 ELSE 0 END) as negative,
            COUNT(*) as total
        FROM matches m
        JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
        WHERE m.keyword_value = %s
        AND bp.posted_at >= %s
        AND bp.sentiment_score IS NOT NULL
    """, (keyword, cutoff_time))

    row = cur.fetchone()
    cur.close()

    if row and row[3] > 0:  # row[3] is total
        total = row[3]
        return {
            "positive": round((row[0] / total) * 100),
            "neutral": round((row[1] / total) * 100),
            "negative": round((row[2] / total) * 100),
            "total": total
        }

    return {"positive": 0, "neutral": 0, "negative": 0, "total": 0}


def get_llm_summary(conn: psycopg2.extensions.connection, user_id: int) -> str | None:
    """Fetches the latest LLM-generated summary for a user."""
    cur = conn.cursor()

    cur.execute("""
        SELECT summary
        FROM llm_summary
        WHERE user_id = %s
        ORDER BY summary_id DESC
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()
    cur.close()

    return row[0] if row else None


def calculate_trend(conn: psycopg2.extensions.connection, current: int, previous: int) -> dict:
    """Calculates the trend direction and percentage change."""
    if previous == 0:
        if current > 0:
            return {"direction": "up", "percent": 100, "symbol": "↑"}
        return {"direction": "stable", "percent": 0, "symbol": "→"}

    change = ((current - previous) / previous) * 100

    if change > 5:
        return {"direction": "up", "percent": round(change), "symbol": "↑"}
    elif change < -5:
        return {"direction": "down", "percent": round(abs(change)), "symbol": "↓"}
    else:
        return {"direction": "stable", "percent": round(abs(change)), "symbol": "→"}


def get_keyword_stats(conn: psycopg2.extensions.connection, keyword: str) -> dict:
    """Fetches all stats for a single keyword."""
    posts_24h = get_post_count(conn, keyword, hours=24)
    posts_7d = get_post_count(conn, keyword, hours=168)
    posts_previous_7d = get_post_count_between(
        conn, keyword, start_hours_ago=336, end_hours_ago=168)

    sentiment = get_sentiment_breakdown(conn, keyword, hours=168)
    trend = calculate_trend(conn, posts_7d, posts_previous_7d)
    return {
        "keyword": keyword,
        "posts_24h": posts_24h,
        "posts_7d": posts_7d,
        "posts_previous_7d": posts_previous_7d,
        "sentiment": sentiment,
        "trend": trend
    }


def get_user_report_data(conn: psycopg2.extensions.connection, user_id: int) -> dict:
    """Fetches all report data for a single user."""
    keywords = get_user_keywords(conn, user_id)

    keyword_stats = [get_keyword_stats(conn, kw) for kw in keywords]

    # Calculate totals
    total_posts_24h = sum(ks["posts_24h"] for ks in keyword_stats)
    total_posts_7d = sum(ks["posts_7d"] for ks in keyword_stats)

    # Average sentiment across all keywords
    total_sentiment_posts = sum(ks["sentiment"]["total"]
                                for ks in keyword_stats)
    if total_sentiment_posts > 0:
        avg_positive = sum(ks["sentiment"]["positive"] * ks["sentiment"]["total"]
                           for ks in keyword_stats) / total_sentiment_posts
    else:
        avg_positive = 0

    llm_summary = get_llm_summary(conn, user_id)

    return {
        "user_id": user_id,
        "keywords": keyword_stats,
        "totals": {
            "posts_24h": total_posts_24h,
            "posts_7d": total_posts_7d,
            "avg_positive_sentiment": round(avg_positive)
        },
        "llm_summary": llm_summary
    }

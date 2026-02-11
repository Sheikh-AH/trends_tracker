"""Database query functions for metrics, posts, and sentiment data."""

import logging
import os
from datetime import datetime, timedelta

import psycopg2
import streamlit as st
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)
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
    """Extract post texts from the last N days for a keyword as a single corpus."""
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

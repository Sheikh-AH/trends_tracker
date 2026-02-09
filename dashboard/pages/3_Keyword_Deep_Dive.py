"""Keyword Deep Dive - Detailed analytics for individual keywords."""

import altair as alt
import pandas as pd
import streamlit as st

# Import shared functions from utils module
from utils import (
    get_db_connection,
    get_user_keywords,
)
from psycopg2.extras import RealDictCursor


def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Keyword Deep Dive - Trends Tracker",
        page_icon="🔍",
        layout="wide"
    )

    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


def load_keywords():
    """Load keywords from database if needed."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else [
                "matcha", "boba", "coffee"]
            st.session_state.keywords_loaded = True


def render_filters():
    """Render filter dropdowns for keyword and time period selection."""
    col1, col2 = st.columns(2)

    with col1:
        selected_keyword = st.selectbox(
            "Select Keyword",
            options=st.session_state.get("keywords", []),
            key="selected_keyword",
            help="Choose a keyword to analyze"
        )

    with col2:
        time_periods = {
            "7 days": 7,
            "14 days": 14,
            "30 days": 30,
            "90 days": 90,
            "6 months": 180,
            "1 year": 365
        }
        selected_period = st.selectbox(
            "Select Time Period",
            options=list(time_periods.keys()),
            key="selected_period",
            help="Choose the time range for analysis"
        )
        days = time_periods[selected_period]

    return selected_keyword, days


def render_activity_over_time(keyword: str, days: int):
    """Render a multi-line chart showing posts, replies, and total activity over time."""
    conn = get_db_connection()
    if not conn:
        st.error("Unable to connect to database")
        return

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT 
                DATE(bp.posted_at) AS date,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NULL) AS posts,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL) AS replies,
                COUNT(*) AS total
            FROM bluesky_posts bp
            JOIN matches m ON bp.post_uri = m.post_uri
            WHERE LOWER(m.keyword_value) = LOWER(%s)
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
            GROUP BY DATE(bp.posted_at)
            ORDER BY DATE(bp.posted_at)
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()

        if not results:
            st.warning(
                f"No data available for '{keyword}' in the last {days} days")
            return

        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["date"])

        df_long = df.melt(
            id_vars=["date"],
            value_vars=["posts", "replies", "total"],
            var_name="type",
            value_name="count"
        )

        chart = (
            alt.Chart(df_long)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("count:Q", title="Count"),
                color=alt.Color(
                    "type:N",
                    title="Metric",
                    scale=alt.Scale(
                        domain=["posts", "replies", "total"],
                        range=["#1f77b4", "#ff7f0e", "#2ca02c"]
                    )
                ),
                tooltip=[
                    alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                    alt.Tooltip("type:N", title="Type"),
                    alt.Tooltip("count:Q", title="Count")
                ]
            )
            .properties(
                width="container",
                height=350
            )
            .interactive()
        )

        return chart

    except Exception as e:
        conn.rollback()
        st.error(f"Error fetching activity data: {e}")
    finally:
        if cursor:
            cursor.close()


def render_sentiment_distribution(keyword: str, days: int):
    """Render a donut chart showing sentiment distribution."""
    conn = get_db_connection()
    if not conn:
        st.error("Unable to connect to database")
        return

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT
                CASE
                    WHEN bp.sentiment_score::float > 0.1 THEN 'Positive'
                    WHEN bp.sentiment_score::float < -0.1 THEN 'Negative'
                    ELSE 'Neutral'
                END AS sentiment,
                COUNT(*) AS count
            FROM bluesky_posts bp
            JOIN matches m ON bp.post_uri = m.post_uri
            WHERE LOWER(m.keyword_value) = LOWER(%s)
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
              AND bp.sentiment_score IS NOT NULL
            GROUP BY sentiment;
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()

        if not results:
            st.warning("No sentiment data available for this period.")
            return

        df = pd.DataFrame(results)

        chart = (
            alt.Chart(df)
            .mark_arc(innerRadius=70)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color(
                    "sentiment:N",
                    scale=alt.Scale(
                        domain=["Positive", "Neutral", "Negative"],
                        range=["#2ca02c", "#9e9e9e", "#d62728"]
                    )
                ),
                tooltip=[
                    alt.Tooltip("sentiment:N", title="Sentiment"),
                    alt.Tooltip("count:Q", title="Posts")
                ]
            )
            .properties(
                width=400,
                height=350
            )
        )

        return chart

    except Exception as e:
        conn.rollback()
        st.error(f"Error fetching sentiment data: {e}")
    finally:
        if cursor:
            cursor.close()


def render_sentiment_over_time(keyword: str, days: int, window: int = 7):
    """Render a rolling average sentiment score over time."""
    conn = get_db_connection()
    if not conn:
        st.error("Unable to connect to database")
        return

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            WITH daily_sentiment AS (
                SELECT
                    DATE(bp.posted_at) AS date,
                    AVG(NULLIF(bp.sentiment_score, '')::float) AS avg_sentiment
                FROM bluesky_posts bp
                JOIN matches m ON bp.post_uri = m.post_uri
                WHERE LOWER(m.keyword_value) = LOWER(%s)
                  AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
                  AND bp.sentiment_score IS NOT NULL
                GROUP BY DATE(bp.posted_at)
            )
            SELECT
                date,
                AVG(avg_sentiment) OVER (
                    ORDER BY date
                    ROWS BETWEEN %s PRECEDING AND CURRENT ROW
                ) AS rolling_sentiment
            FROM daily_sentiment
            ORDER BY date;
        """
        cursor.execute(query, (keyword, days, window - 1))
        results = cursor.fetchall()

        if not results:
            st.warning("No sentiment trend data available for this period.")
            return

        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["date"])

        line_chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("rolling_sentiment:Q",
                        title=f"{window}-Day Rolling Avg Sentiment", scale=alt.Scale(domain=[-1, 1])),
                tooltip=[
                    alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                    alt.Tooltip("rolling_sentiment:Q", format=".2f",
                                title="Rolling Avg Sentiment")
                ]
            )
            .interactive()
        )

        zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            strokeDash=[4, 4], color="gray").encode(y="y:Q")

        layered_chart = (line_chart + zero_line).properties(
            title=f"Sentiment Over Time ({window}-Day Rolling Avg) – {keyword.title()}",
            width="container",
            height=350
        )

        return layered_chart

    except Exception as e:
        conn.rollback()
        st.error(f"Error fetching sentiment trend data: {e}")
    finally:
        if cursor:
            cursor.close()


def render_kpi_metrics(keyword: str, days: int):
    """Render KPI metrics for the selected keyword."""
    conn = get_db_connection()
    if not conn:
        st.error("Unable to connect to database")
        return

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT
                COUNT(*) AS total_mentions,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NULL) AS posts,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL) AS replies,
                AVG(NULLIF(bp.sentiment_score, '')::float) AS avg_sentiment,
                COUNT(*) FILTER (
                    WHERE NULLIF(bp.sentiment_score, '')::float > 0.1
                )::float / COUNT(*) AS pct_positive,
                COUNT(*) FILTER (
                    WHERE NULLIF(bp.sentiment_score, '')::float < -0.1
                )::float / COUNT(*) AS pct_negative
            FROM bluesky_posts bp
            JOIN matches m ON bp.post_uri = m.post_uri
            WHERE LOWER(m.keyword_value) = LOWER(%s)
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s;
        """
        cursor.execute(query, (keyword, days))
        data = cursor.fetchone()

        if not data or data["total_mentions"] == 0:
            st.warning("No KPI data available.")
            return

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        col1.metric("Total Mentions", f"{data['total_mentions']:,}")
        col2.metric("Posts", f"{data['posts']:,}")
        col3.metric("Replies", f"{data['replies']:,}")
        col4.metric(
            "Avg Sentiment", f"{data['avg_sentiment']:.2f}" if data["avg_sentiment"] is not None else "—")
        col5.metric("Positive %", f"{data['pct_positive'] * 100:.1f}%")
        col6.metric("Negative %", f"{data['pct_negative'] * 100:.1f}%")

    except Exception as e:
        conn.rollback()
        st.error(f"Error fetching KPI metrics: {e}")
    finally:
        if cursor:
            cursor.close()


def render_sentiment_volume_quadrant(keyword: str, days: int):
    """Render sentiment vs volume quadrant chart."""
    conn = get_db_connection()
    if not conn:
        st.error("Unable to connect to database")
        return

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT
                DATE(bp.posted_at) AS date,
                COUNT(*) AS volume,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL) AS replies,
                AVG(NULLIF(bp.sentiment_score, '')::float) AS avg_sentiment
            FROM bluesky_posts bp
            JOIN matches m ON bp.post_uri = m.post_uri
            WHERE LOWER(m.keyword_value) = LOWER(%s)
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
              AND bp.sentiment_score IS NOT NULL
            GROUP BY DATE(bp.posted_at)
            ORDER BY DATE(bp.posted_at);
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()

        if not results:
            st.warning("No data available for sentiment-volume analysis.")
            return

        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["date"])

        chart = (
            alt.Chart(df)
            .mark_circle(opacity=0.8)
            .encode(
                x=alt.X("volume:Q", title="Daily Volume"),
                y=alt.Y("avg_sentiment:Q", title="Average Sentiment",
                        scale=alt.Scale(domain=[-1, 1])),
                size=alt.Size("replies:Q", title="Replies",
                              scale=alt.Scale(range=[100, 1200])),
                color=alt.Color("date:T", title="Date",
                                scale=alt.Scale(scheme="blues")),
                tooltip=[
                    alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                    alt.Tooltip("volume:Q", title="Mentions"),
                    alt.Tooltip("replies:Q", title="Replies"),
                    alt.Tooltip("avg_sentiment:Q", format=".2f",
                                title="Avg Sentiment")
                ]
            )
            .properties(width="container", height=350)
        )

        vline = alt.Chart(pd.DataFrame({"x": [df["volume"].mean()]})).mark_rule(
            strokeDash=[4, 4], color="gray").encode(x="x:Q")
        hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            strokeDash=[4, 4], color="gray").encode(y="y:Q")

        layered_chart = (chart + vline + hline).properties(
            title=f"Sentiment × Volume – {keyword.title()}",
            width="container",
            height=350
        )

        return layered_chart

    except Exception as e:
        conn.rollback()
        st.error(f"Error fetching sentiment-volume data: {e}")
    finally:
        if cursor:
            cursor.close()


if __name__ == "__main__":
    configure_page()
    load_keywords()

    st.title("🔍 Keyword Deep Dive")
    st.markdown("Detailed analytics and insights for individual keywords")
    st.markdown("---")

    selected_keyword, days = render_filters()
    st.markdown("---")

    render_kpi_metrics(selected_keyword, days)
    st.markdown("---")

    # Side by side: activity + sentiment distribution
    col1, col2 = st.columns([2, 1])
    activity_chart = render_activity_over_time(selected_keyword, days)
    sentiment_chart = render_sentiment_distribution(selected_keyword, days)
    if activity_chart:
        col1.altair_chart(activity_chart, use_container_width=True)
    if sentiment_chart:
        col2.altair_chart(sentiment_chart, use_container_width=True)

    st.markdown("---")

    # Side by side: sentiment trend + sentiment × volume
    col1, col2 = st.columns(2)
    sentiment_trend_chart = render_sentiment_over_time(selected_keyword, days)
    sentiment_volume_chart = render_sentiment_volume_quadrant(
        selected_keyword, days)
    if sentiment_trend_chart:
        col1.altair_chart(sentiment_trend_chart, use_container_width=True)
    if sentiment_volume_chart:
        col2.altair_chart(sentiment_volume_chart, use_container_width=True)

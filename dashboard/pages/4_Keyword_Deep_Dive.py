"""Keyword Deep Dive - Detailed analytics for individual keywords."""

import altair as alt
import pandas as pd
import streamlit as st

# Import shared functions from utils module
from utils import (
    get_db_connection,
    get_user_keywords,
    _load_sql_query
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
            st.session_state.keywords = db_keywords
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


@st.cache_data(ttl=3600)
def get_daily_analytics(keyword: str, days: int):
    """
    Fetch daily analytics: posts, replies, total, and average sentiment by date.
    Used for: activity over time, sentiment over time, sentiment × volume charts.
    """
    conn = get_db_connection()
    if not conn:
        return None

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT
                DATE(bp.posted_at) AS date,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NULL) AS posts,
                COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL) AS replies,
                AVG(NULLIF(bp.sentiment_score, '')::float) AS avg_sentiment
            FROM bluesky_posts bp
            JOIN matches m ON bp.post_uri = m.post_uri
            WHERE m.keyword_value = %s
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
            GROUP BY DATE(bp.posted_at)
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()
        return pd.DataFrame(results) if results else pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching daily analytics: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()


@st.cache_data(ttl=3600)
def get_sentiment_distribution(keyword: str, days: int):
    """
    Fetch sentiment distribution: counts of Positive, Negative, Neutral.
    Used for: sentiment donut chart and KPI metrics.
    """
    conn = get_db_connection()
    if not conn:
        return None

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
            WHERE m.keyword_value = %s
              AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
              AND bp.sentiment_score IS NOT NULL
            GROUP BY sentiment
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()
        return pd.DataFrame(results) if results else pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching sentiment distribution: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()


def compute_kpi_metrics(df_daily: pd.DataFrame, df_sentiment: pd.DataFrame):
    """Compute KPI metrics from daily analytics and sentiment distribution."""
    if df_daily.empty or df_sentiment.empty:
        return None

    metrics = {}

    # From daily analytics
    metrics['total_mentions'] = int(df_daily['total'].sum())
    metrics['posts'] = int(df_daily['posts'].sum())
    metrics['replies'] = int(df_daily['replies'].sum())
    metrics['avg_sentiment'] = float(df_daily['avg_sentiment'].mean())

    # From sentiment distribution
    total_sentiment = df_sentiment['count'].sum()
    positive_count = df_sentiment[df_sentiment['sentiment']
                                  == 'Positive']['count'].sum()
    negative_count = df_sentiment[df_sentiment['sentiment']
                                  == 'Negative']['count'].sum()

    metrics['pct_positive'] = float(
        positive_count / total_sentiment) if total_sentiment > 0 else 0
    metrics['pct_negative'] = float(
        negative_count / total_sentiment) if total_sentiment > 0 else 0

    return metrics


def render_activity_over_time(df_daily: pd.DataFrame, keyword: str):
    """Render a multi-line chart showing posts, replies, and total activity over time."""
    if df_daily.empty:
        st.warning(f"No data available for '{keyword}' in the last period")
        return None

    df_daily["date"] = pd.to_datetime(df_daily["date"])

    df_long = df_daily.melt(
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


def render_sentiment_distribution(df_sentiment: pd.DataFrame, keyword: str):
    """Render a donut chart showing sentiment distribution."""
    if df_sentiment.empty:
        st.warning("No sentiment data available for this period.")
        return None

    chart = (
        alt.Chart(df_sentiment)
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


def render_sentiment_over_time(df_daily: pd.DataFrame, keyword: str, window: int = 7):
    """Render a rolling average sentiment score over time."""
    if df_daily.empty:
        st.warning("No sentiment trend data available for this period.")
        return None

    df_daily_sorted = df_daily.sort_values("date").copy()
    df_daily_sorted["date"] = pd.to_datetime(df_daily_sorted["date"])
    df_daily_sorted["rolling_sentiment"] = df_daily_sorted["avg_sentiment"].rolling(
        window=window, min_periods=1
    ).mean()

    line_chart = (
        alt.Chart(df_daily_sorted)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d")),
            y=alt.Y(
                "rolling_sentiment:Q",
                title=f"{window}-Day Rolling Avg Sentiment",
                scale=alt.Scale(domain=[-1, 1])
            ),
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


def render_kpi_metrics(metrics: dict, keyword: str):
    """Render KPI metrics for the selected keyword."""
    if not metrics or metrics["total_mentions"] == 0:
        st.warning("No KPI data available.")
        return

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Total Mentions", f"{metrics['total_mentions']:,}")
    col2.metric("Posts", f"{metrics['posts']:,}")
    col3.metric("Replies", f"{metrics['replies']:,}")
    col4.metric(
        "Avg Sentiment", f"{metrics['avg_sentiment']:.2f}" if metrics["avg_sentiment"] is not None else "—")
    col5.metric("Positive %", f"{metrics['pct_positive'] * 100:.1f}%")
    col6.metric("Negative %", f"{metrics['pct_negative'] * 100:.1f}%")


def render_sentiment_volume_quadrant(df_daily: pd.DataFrame, keyword: str):
    """Render sentiment vs volume quadrant chart."""
    if df_daily.empty:
        st.warning("No data available for sentiment-volume analysis.")
        return None

    df_daily["date"] = pd.to_datetime(df_daily["date"])

    chart = (
        alt.Chart(df_daily)
        .mark_circle(opacity=0.8)
        .encode(
            x=alt.X("total:Q", title="Daily Volume"),
            y=alt.Y("avg_sentiment:Q", title="Average Sentiment",
                    scale=alt.Scale(domain=[-1, 1])),
            size=alt.Size("replies:Q", title="Replies",
                          scale=alt.Scale(range=[100, 1200])),
            color=alt.Color("date:T", title="Date",
                            scale=alt.Scale(scheme="tableau10")),
            tooltip=[
                alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                alt.Tooltip("total:Q", title="Mentions"),
                alt.Tooltip("replies:Q", title="Replies"),
                alt.Tooltip("avg_sentiment:Q", format=".2f",
                            title="Avg Sentiment")
            ]
        )
        .properties(width="container", height=350)
    )

    vline = alt.Chart(pd.DataFrame({"x": [df_daily["total"].mean()]})).mark_rule(
        strokeDash=[4, 4], color="gray").encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[4, 4], color="gray").encode(y="y:Q")

    layered_chart = (chart + vline + hline).properties(
        title=f"Sentiment × Volume – {keyword.title()}",
        width="container",
        height=350
    )

    return layered_chart


if __name__ == "__main__":
    configure_page()
    load_keywords()

    st.title("Keyword Deep Dive")
    st.markdown("Detailed analytics and insights for individual keywords")
    st.markdown("---")

    selected_keyword, days = render_filters()
    st.markdown("---")

    # Fetch the two cached queries
    df_daily = get_daily_analytics(selected_keyword, days)
    df_sentiment = get_sentiment_distribution(selected_keyword, days)

    # Compute KPI metrics from cached data
    metrics = compute_kpi_metrics(df_daily, df_sentiment)

    # Render KPI metrics
    render_kpi_metrics(metrics, selected_keyword)
    st.markdown("---")

    # Side by side: activity + sentiment distribution
    col1, col2 = st.columns([2, 1])
    activity_chart = render_activity_over_time(df_daily, selected_keyword)
    sentiment_chart = render_sentiment_distribution(
        df_sentiment, selected_keyword)
    if activity_chart:
        col1.altair_chart(activity_chart, use_container_width=True)
    if sentiment_chart:
        col2.altair_chart(sentiment_chart, use_container_width=True)

    st.markdown("---")

    # Side by side: sentiment trend + sentiment × volume
    col1, col2 = st.columns(2)
    sentiment_trend_chart = render_sentiment_over_time(
        df_daily, selected_keyword)
    sentiment_volume_chart = render_sentiment_volume_quadrant(
        df_daily, selected_keyword)
    if sentiment_trend_chart:
        col1.altair_chart(sentiment_trend_chart, use_container_width=True)
    if sentiment_volume_chart:
        col2.altair_chart(sentiment_volume_chart, use_container_width=True)

# pylint: disable=import-error
"""Keyword Deep Dive - Detailed analytics for individual keywords."""

import altair as alt
import pandas as pd
import streamlit as st
from psycopg2.extras import RealDictCursor
from db_utils import get_db_connection
from keyword_utils import get_user_keywords
from ui_helper_utils import render_sidebar


def configure_page() -> None:
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


def should_load_keywords() -> bool:
    """Check if keywords should be loaded."""
    return not st.session_state.get("keywords_loaded", False)


def fetch_keywords() -> list:
    """Fetch keywords for the current user."""
    conn = get_db_connection()
    if not conn or not st.session_state.get("user_id"):
        return []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    db_keywords = get_user_keywords(cursor, st.session_state.user_id)
    cursor.close()
    return db_keywords


def load_keywords() -> None:
    """Load keywords from database if needed."""
    if should_load_keywords():
        st.session_state.keywords = fetch_keywords()
        st.session_state.keywords_loaded = True


def time_periods() -> dict:
    """Return supported time periods."""
    return {
        "7 days": 7,
        "14 days": 14,
        "30 days": 30,
        "90 days": 90,
        "6 months": 180,
        "1 year": 365
    }


def select_keyword() -> str:
    """Render keyword select box."""
    return st.selectbox(
        "Select Keyword",
        options=st.session_state.get("keywords", []),
        key="selected_keyword",
        help="Choose a keyword to analyze"
    )


def select_period() -> int:
    """Render time period select box."""
    periods = time_periods()
    selected = st.selectbox(
        "Select Time Period",
        options=list(periods.keys()),
        key="selected_period",
        help="Choose the time range for analysis"
    )
    return periods[selected]


def render_filters() -> tuple:
    """Render filter dropdowns for keyword and time period selection."""
    col1, col2 = st.columns(2)
    with col1:
        keyword = select_keyword()
    with col2:
        days = select_period()
    return keyword, days


@st.cache_data(ttl=3600)
def get_daily_analytics(keyword: str, days: int) -> pd.DataFrame:
    """Fetch daily analytics by date."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
        cursor.close()


@st.cache_data(ttl=3600)
def get_sentiment_distribution(keyword: str, days: int) -> pd.DataFrame:
    """Fetch sentiment distribution counts."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
        cursor.close()


def sentiment_counts(df_sentiment: pd.DataFrame) -> tuple:
    """Return positive and negative counts."""
    pos = df_sentiment[df_sentiment["sentiment"] == "Positive"]["count"].sum()
    neg = df_sentiment[df_sentiment["sentiment"] == "Negative"]["count"].sum()
    return pos, neg


def compute_kpi_metrics(df_daily: pd.DataFrame, df_sentiment: pd.DataFrame) -> dict | None:
    """Compute KPI metrics from daily analytics and sentiment distribution."""
    if df_daily.empty or df_sentiment.empty:
        return None
    total_sentiment = df_sentiment["count"].sum()
    positive_count, negative_count = sentiment_counts(df_sentiment)
    return {
        "total_mentions": int(df_daily["total"].sum()),
        "posts": int(df_daily["posts"].sum()),
        "replies": int(df_daily["replies"].sum()),
        "avg_sentiment": float(df_daily["avg_sentiment"].mean()),
        "pct_positive": float(positive_count / total_sentiment) if total_sentiment else 0,
        "pct_negative": float(negative_count / total_sentiment) if total_sentiment else 0,
    }


def format_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure date column is datetime."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df


def daily_long(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Return long-form daily metrics sorted by date."""
    df_long = df_daily.melt(
        id_vars=["date"],
        value_vars=["posts", "replies", "total"],
        var_name="type",
        value_name="count"
    )
    return df_long.sort_values("date")


def render_activity_over_time(df_daily: pd.DataFrame, keyword: str):
    """Render a multi-line chart for activity over time."""
    if df_daily.empty:
        st.warning(f"No data available for '{keyword}' in the last period")
        return None
    df_long = daily_long(format_dates(df_daily)).sort_values("date")
    return (
        alt.Chart(df_long)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d"), sort="ascending"),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color(
                "type:N",
                title="Metric",
                scale=alt.Scale(
                    domain=["posts", "replies", "total"],
                    range=["#1f77b4", "#ff7f0e", "#2ca02c"]
                )
            ),
            order=alt.Order("date:T"),
            tooltip=[
                alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                alt.Tooltip("type:N", title="Type"),
                alt.Tooltip("count:Q", title="Count")
            ]
        )
        .properties(width="container", height=350)
        .interactive()
    )


def render_sentiment_distribution(df_sentiment: pd.DataFrame, keyword: str):
    """Render a donut chart showing sentiment distribution."""
    if df_sentiment.empty:
        st.warning("No sentiment data available for this period.")
        return None
    return (
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
        .properties(width=400, height=350)
    )


def rolling_sentiment(df_daily: pd.DataFrame, window: int) -> pd.DataFrame:
    """Compute rolling sentiment."""
    df = format_dates(df_daily).sort_values("date")
    df["rolling_sentiment"] = df["avg_sentiment"].rolling(
        window=window, min_periods=1
    ).mean()
    return df


def render_sentiment_over_time(df_daily: pd.DataFrame, keyword: str, window: int = 7):
    """Render a rolling average sentiment score over time."""
    if df_daily.empty:
        st.warning("No sentiment trend data available for this period.")
        return None
    df = rolling_sentiment(df_daily, window)
    line_chart = (
        alt.Chart(df)
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
    return (line_chart + zero_line).properties(
        title=f"Sentiment Over Time ({window}-Day Rolling Avg) – {keyword.title()}",
        width="container",
        height=350
    )


def render_kpi_metrics(metrics: dict | None, keyword: str) -> None:
    """Render KPI metrics for the selected keyword."""
    if not metrics or metrics["total_mentions"] == 0:
        st.warning("No KPI data available.")
        return
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Mentions", f"{metrics['total_mentions']:,}")
    col2.metric("Posts", f"{metrics['posts']:,}")
    col3.metric("Replies", f"{metrics['replies']:,}")
    col4.metric(
        "Avg Sentiment",
        f"{metrics['avg_sentiment']:.2f}" if metrics["avg_sentiment"] is not None else "—"
    )
    col5.metric("Positive %", f"{metrics['pct_positive'] * 100:.1f}%")
    col6.metric("Negative %", f"{metrics['pct_negative'] * 100:.1f}%")


def volume_reference_lines(df_daily: pd.DataFrame):
    """Create volume and sentiment reference lines."""
    vline = alt.Chart(pd.DataFrame({"x": [df_daily["total"].mean()]})).mark_rule(
        strokeDash=[4, 4], color="gray").encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[4, 4], color="gray").encode(y="y:Q")
    return vline, hline


def render_sentiment_volume_quadrant(df_daily: pd.DataFrame, keyword: str):
    """Render sentiment vs volume quadrant chart."""
    if df_daily.empty:
        st.warning("No data available for sentiment-volume analysis.")
        return None
    df_daily = format_dates(df_daily)
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
    vline, hline = volume_reference_lines(df_daily)
    return (chart + vline + hline).properties(
        title=f"Sentiment × Volume – {keyword.title()}",
        width="container",
        height=350
    )


def render_header() -> None:
    """Render page header."""
    st.title("Keyword Deep Dive")
    st.markdown("Detailed analytics and insights for individual keywords")
    st.markdown("---")


def fetch_data(selected_keyword: str, days: int) -> tuple:
    """Fetch cached query data."""
    df_daily = get_daily_analytics(selected_keyword, days)
    df_sentiment = get_sentiment_distribution(selected_keyword, days)
    return df_daily, df_sentiment


def render_activity_and_sentiment(df_daily: pd.DataFrame, df_sentiment: pd.DataFrame, keyword: str) -> None:
    """Render activity and sentiment charts."""
    col1, col2 = st.columns([2, 1])
    activity_chart = render_activity_over_time(df_daily, keyword)
    sentiment_chart = render_sentiment_distribution(df_sentiment, keyword)
    if activity_chart:
        col1.altair_chart(activity_chart, use_container_width=True)
    if sentiment_chart:
        col2.altair_chart(sentiment_chart, use_container_width=True)


def render_trends_and_quadrant(df_daily: pd.DataFrame, keyword: str) -> None:
    """Render sentiment trend and volume quadrant charts."""
    col1, col2 = st.columns(2)
    sentiment_trend_chart = render_sentiment_over_time(df_daily, keyword)
    sentiment_volume_chart = render_sentiment_volume_quadrant(
        df_daily, keyword)
    if sentiment_trend_chart:
        col1.altair_chart(sentiment_trend_chart, use_container_width=True)
    if sentiment_volume_chart:
        col2.altair_chart(sentiment_volume_chart, use_container_width=True)


# ...existing code...

@st.cache_data(ttl=3600)
def get_google_trends_data(keyword: str, days: int) -> pd.DataFrame:
    """Fetch Google Trends search volume for a keyword over a time period."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
            SELECT
                DATE(gt.trend_date) AS date,
                gt.search_volume
            FROM google_trends gt
            WHERE gt.keyword_value = %s
              AND gt.trend_date >= NOW() - INTERVAL '1 day' * %s
            ORDER BY gt.trend_date
        """
        cursor.execute(query, (keyword, days))
        results = cursor.fetchall()
        return pd.DataFrame(results) if results else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching Google Trends data: {e}")
        return pd.DataFrame()
    finally:
        cursor.close()


# ...existing code...

def render_google_search_volume(keyword: str, days: int) -> None:
    """Render a Google Trends search volume line chart for the selected keyword."""
    df_trends = get_google_trends_data(keyword, days)

    col_title, col_info = st.columns([6, 1])
    with col_title:
        st.subheader(f"Google Trends – {keyword.title()}")
    with col_info:
        st.markdown("")
        with st.popover("ℹ️"):
            st.markdown(
                """
                **Google Search Volume** represents the relative popularity
                of a search term on Google over time.

                - Values are scaled from **0 to 100**, where **100** is the
                  peak popularity during the selected period.
                - A value of **50** means the term was half as popular as
                  the peak.
                - A value of **0** means there was not enough data for that day.

                This data is sourced from **Google Trends** and is useful for
                understanding public interest alongside social media activity.
                """
            )

    if df_trends.empty:
        st.warning(f"No Google Trends data available for '{keyword}'.")
        return

    df_trends["date"] = pd.to_datetime(df_trends["date"])

    chart = (
        alt.Chart(df_trends)
        .mark_area(
            line={"color": "#4285F4"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#4285F4", offset=1),
                    alt.GradientStop(color="rgba(66,133,244,0.1)", offset=0),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
            interpolate="monotone",
        )
        .encode(
            x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d")),
            y=alt.Y("search_volume:Q", title="Search Volume"),
            tooltip=[
                alt.Tooltip("date:T", format="%B %d, %Y", title="Date"),
                alt.Tooltip("search_volume:Q",
                            title="Search Volume", format=","),
            ],
        )
        .properties(
            width="container",
            height=350,
        )
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    configure_page()
    load_keywords()
    render_sidebar()
    render_header()
    selected_keyword, days = render_filters()
    st.markdown("---")
    df_daily, df_sentiment = fetch_data(selected_keyword, days)
    metrics = compute_kpi_metrics(df_daily, df_sentiment)
    render_kpi_metrics(metrics, selected_keyword)
    st.markdown("---")
    render_activity_and_sentiment(df_daily, df_sentiment, selected_keyword)
    st.markdown("---")
    render_trends_and_quadrant(df_daily, selected_keyword)
    st.markdown("---")
    render_google_search_volume(selected_keyword, days)

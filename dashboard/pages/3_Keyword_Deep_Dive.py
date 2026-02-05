"""
Keyword Deep Dive - Detailed analytics for individual keywords.
"""

import random
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

# Import shared functions from utils module
import sys
from utils import (
    get_db_connection,
    get_user_keywords,
    generate_placeholder_metrics,
    generate_time_series_data,
    generate_sentiment_breakdown,
    generate_keywords_summary,
    render_sidebar
)
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Keyword Deep Dive - Trends Tracker",
        page_icon="🔍",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Helper Functions ==============

def load_keywords():
    """Load keywords from database if needed."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else ["matcha", "boba", "coffee"]
            st.session_state.keywords_loaded = True


def render_kpi_metrics(metrics: dict):
    """Render KPI metrics row."""
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


def render_activity_chart(time_data: pd.DataFrame):
    """Render activity over time chart."""
    st.markdown("### 📈 Activity Metrics Over Time")

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


def render_sentiment_chart(sentiment_data: dict):
    """Render sentiment breakdown chart."""
    st.markdown("### 🎭 Sentiment Breakdown")

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


def render_sentiment_trend(time_data: pd.DataFrame):
    """Render sentiment trend over time."""
    st.markdown("### 📊 Overall Sentiment Score Over Time")

    time_data["sentiment"] = [round(random.uniform(-0.5, 0.8), 2) for _ in range(len(time_data))]

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

    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[5, 5], color="gray"
    ).encode(y="y:Q")

    st.altair_chart(sentiment_area + zero_line, use_container_width=True)


def render_daily_averages(time_data: pd.DataFrame):
    """Render daily averages bar chart."""
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


def render_comparison_chart(keywords: list, days: int):
    """Render keyword comparison chart."""
    st.markdown("### 🔍 Keyword Mentions Comparison")

    if len(keywords) > 0:
        comparison_data = pd.DataFrame({
            "Keyword": keywords,
            "Mentions": [generate_placeholder_metrics(kw, days)["mentions"] for kw in keywords]
        })

        comparison_chart = alt.Chart(comparison_data).mark_bar().encode(
            x=alt.X("Keyword:N", title="Keyword"),
            y=alt.Y("Mentions:Q", title="Mentions"),
            color=alt.Color("Keyword:N", scale=alt.Scale(scheme="set2"), legend=None),
            tooltip=["Keyword:N", "Mentions:Q"]
        ).properties(height=300)

        st.altair_chart(comparison_chart, use_container_width=True)
    else:
        st.info("Add keywords in the Manage Topics page to see comparison data.")


def render_summary_table(keywords: list, days: int):
    """Render keywords summary table."""
    st.markdown("### 📋 Keywords Summary Table")

    if len(keywords) > 0:
        summary_df = generate_keywords_summary(keywords, days)

        def color_sentiment(val):
            if val > 0.2:
                return "background-color: #d4edda"
            elif val < -0.2:
                return "background-color: #f8d7da"
            return ""

        styled_df = summary_df.style.map(
            color_sentiment, subset=["Avg Sentiment"]
        ).format({"Avg Sentiment": "{:.2f}"})

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("Add keywords in the Manage Topics page to see summary data.")


# ============== Main Function ==============

def main():
    """Main function for the Keyword Deep Dive page."""
    st.title("🔍 Keyword Deep Dive")
    st.markdown("Detailed analytics and insights for your tracked keywords.")

    # Load keywords
    load_keywords()

    # Top controls row
    col1, col2, _ = st.columns([2, 2, 4])

    with col1:
        keywords = st.session_state.get("keywords", ["matcha", "boba", "coffee"])
        if keywords:
            selected_keyword = st.selectbox("Select Keyword", options=keywords, index=0)
        else:
            st.warning("No keywords tracked. Add some in Manage Topics.")
            st.stop()

    with col2:
        days_options = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}
        selected_period = st.selectbox("Time Period", options=list(days_options.keys()))
        days = days_options[selected_period]

    st.markdown("---")

    # KPI Metrics Row
    metrics = generate_placeholder_metrics(selected_keyword, days)
    render_kpi_metrics(metrics)

    st.markdown("---")

    # Charts Row 1: Activity Over Time & Sentiment Breakdown
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        time_data = generate_time_series_data(selected_keyword, days)
        render_activity_chart(time_data)

    with chart_col2:
        sentiment_data = generate_sentiment_breakdown(selected_keyword)
        render_sentiment_chart(sentiment_data)

    st.markdown("---")

    # Charts Row 2: Overall Sentiment & Daily Averages
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        render_sentiment_trend(time_data)

    with chart_col4:
        render_daily_averages(time_data)

    st.markdown("---")

    # Chart Row 3: Keyword Comparison
    render_comparison_chart(keywords, days)

    st.markdown("---")

    # Summary Table
    render_summary_table(keywords, days)

    # Default Sidebar
    # Render shared sidebar
    render_sidebar()


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
configure_page()
if __name__ == "__main__":
    configure_page()
    main()
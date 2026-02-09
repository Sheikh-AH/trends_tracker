"""
Keyword Comparisons - Compare metrics across multiple keywords over time.
"""

import streamlit as st
from streamlit import session_state as ss
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
from utils import (
    get_db_connection,
    get_user_keywords,
    render_sidebar,
    _load_sql_query
)
from psycopg2.extras import RealDictCursor


def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Keyword Comparisons - Trends Tracker",
        page_icon="📊",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


def load_keywords():
    """Load keywords from database if needed."""
    if not ss.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and ss.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, ss.user_id)
            cursor.close()
            ss.keywords = db_keywords if db_keywords else []
            ss.keywords_loaded = True


def get_comparison_data(cursor, keywords: list, days: int) -> pd.DataFrame:
    """Fetch post count and sentiment data over time for selected keywords."""
    if not keywords:
        return pd.DataFrame()

    start_date = datetime.now() - timedelta(days=days)

    query = _load_sql_query("get_keyword_summary.sql")

    cursor.execute(query, (keywords, start_date))
    results = cursor.fetchall()

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df['date'] = pd.to_datetime(df['date'])
    df['avg_sentiment'] = df['avg_sentiment'].astype(float).round(2)

    if df.empty:
        st.info(f"No data available for the selected keywords.")
        st.stop()

    return df


def create_comparison_chart(df: pd.DataFrame, metric: str, events: list) -> alt.LayerChart:
    """Create a line chart comparing keywords with event markers."""

    if df.empty:
        return None

    y_field = "post_count" if metric == "Post Count" else "avg_sentiment"
    y_title = "Post Count" if metric == "Post Count" else "Average Sentiment"

    # Calculate date range with padding
    min_date = df['date'].min()
    max_date = df['date'].max()
    date_range = (max_date - min_date).days
    padded_max_date = max_date + pd.Timedelta(days=max(1, date_range * 0.1))

    max_value = df[y_field].max() + (df[y_field].max() *
                                     0.1)  # Add 10% padding to y-axis

    # Base line chart with padded x-axis
    line_chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X(
            'date:T',
            title='Date',
            scale=alt.Scale(domain=[min_date, padded_max_date])
        ),
        y=alt.Y(f'{y_field}:Q', title=y_title,
                scale=alt.Scale(domain=[0, max_value])),
        color=alt.Color('keyword:N', title='Keyword'),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('keyword:N', title='Keyword'),
            alt.Tooltip(f'{y_field}:Q', title=y_title, format='.2f')
        ]
    ).properties(
        height=400
    )

    # Add event vertical lines if any
    if events:
        events_df = pd.DataFrame(events)
        events_df['date'] = pd.to_datetime(events_df['date'])

        event_rules = alt.Chart(events_df).mark_rule(
            color='red',
            strokeWidth=3,
            opacity=0.6
        ).encode(
            x='date:T',
            tooltip=[
                alt.Tooltip('date:T', title='Event Date', format='%Y-%m-%d'),
                alt.Tooltip('label:N', title='Event')
            ]
        )

        event_labels = alt.Chart(events_df).mark_text(
            align='left',
            baseline='bottom',
            dx=-155,
            dy=-5,
            color='red',
            angle=90,
            fontSize=11,
            fontWeight='bold'
        ).encode(
            x='date:T',
            text='label:N',
        )
        print(1)

        return (line_chart + event_rules + event_labels).interactive()

    return line_chart.interactive()


def render_event_manager():
    """Render the event management UI."""
    if "comparison_events" not in ss:
        ss.comparison_events = []

    st.subheader("Event Markers")

    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        event_date = st.date_input(
            "Event Date",
            value=datetime.now().date(),
            key="new_event_date"
        )

    with col2:
        event_label = st.text_input(
            "Event Label",
            placeholder="e.g., Product Launch",
            key="new_event_label"
        )

    with col3:
        st.write("")  # Spacing
        st.write("")
        if st.button("Add Event", type="primary"):
            if event_label:
                ss.comparison_events.append({
                    "date": event_date.isoformat(),
                    "label": event_label
                })
                st.rerun()
            else:
                st.warning("Please enter an event label.")

    # Display existing events
    if ss.comparison_events:
        st.write("**Current Events:**")
        for i, event in enumerate(ss.comparison_events):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"📍 {event['date']} - {event['label']}")
            with col_b:
                if st.button("Remove", key=f"remove_event_{i}"):
                    ss.comparison_events.pop(i)
                    st.rerun()

def get_selected_keywords():
    """Render the keyword selection multiselect and return the selected keywords."""
    if "comparison_selected_keywords" not in ss:
        ss.comparison_selected_keywords = []

    # Filter out any keywords that are no longer in the user's list
    valid_saved = [
        k for k in ss.comparison_selected_keywords if k in ss.keywords]

    selected_keywords = st.multiselect(
        "Choose two or more keywords",
        options=ss.keywords,
        default=valid_saved,
        key="comparison_keyword_select",
        help="Select keywords to compare their metrics over time"
    )

    # Save selection to session state
    ss.comparison_selected_keywords = selected_keywords

    if len(selected_keywords) < 2:
        st.warning("Please select at least two keywords to compare.")
        st.stop()

    return selected_keywords

def render_controls():
    """Render the metric and time period selection controls."""
    col1, col2 = st.columns([1, 1])

    with col1:
        metric = st.selectbox(
            "Metric",
            options=["Post Count", "Sentiment"],
            index=0,
            help="Choose which metric to display"
        )

    with col2:
        days = st.selectbox(
            "Time Period",
            options=[7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Last {x} days"
        )

    return metric, days

if __name__ == "__main__":
    configure_page()
    render_sidebar()
    load_keywords()

    st.title("Keyword Comparisons")

    # Check if user has keywords
    if not ss.get("keywords"):
        st.info("No keywords tracked. Add keywords from the Profile page to compare.")
        st.stop()

    st.subheader("Select Keywords to Compare")
    selected_keywords = get_selected_keywords()

    metric, days = render_controls()

    # Event management
    with st.expander("Add Event Markers", expanded=False):
        render_event_manager()

    st.divider()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    df = get_comparison_data(cursor, selected_keywords, days)
    cursor.close()

    
    chart = create_comparison_chart(
        df,
        metric,
        ss.get("comparison_events", [])
    )
    if chart:
        st.altair_chart(chart, use_container_width=True)

    # Summary statistics
    st.subheader("Summary Statistics")

    # Calculate metrics for each keyword
    metrics_data = {}
    metrics_numeric = {}  # Store numeric values for highlighting

    for kw in selected_keywords:
        kw_data = df[df['keyword'] == kw]

        total_posts = kw_data['post_count'].sum()
        avg_sentiment = kw_data['avg_sentiment'].mean().round(2)
        sentiment_volatility = kw_data['avg_sentiment'].std().round(2)
        post_volatility = kw_data['post_count'].std().round(2)
        max_sentiment = kw_data['avg_sentiment'].max().round(2)
        min_sentiment = kw_data[kw_data['avg_sentiment']
                                != 0]['avg_sentiment'].min().round(2)
        avg_posts_per_day = (
            total_posts / max(1, len(kw_data))).round(2)

        metrics_data[kw] = {
            'Total Posts': total_posts,
            'Avg Posts/Day': avg_posts_per_day,
            'Post Count Volatility': post_volatility,
            'Avg Sentiment': avg_sentiment,
            'Sentiment Max': max_sentiment,
            'Sentiment Min': min_sentiment,
            'Sentiment Volatility': sentiment_volatility
        }

        metrics_numeric[kw] = {
            'Total Posts': total_posts,
            'Avg Posts/Day': avg_posts_per_day,
            'Post Count Volatility': post_volatility,
            'Avg Sentiment': avg_sentiment,
            'Sentiment Max': max_sentiment,
            'Sentiment Min': min_sentiment,
            'Sentiment Volatility': sentiment_volatility
        }

    # Create comparison table
    metric_names = ['Total Posts', 'Avg Posts/Day', 'Post Count Volatility',
                    'Avg Sentiment', 'Sentiment Max', 'Sentiment Min', 'Sentiment Volatility']

    # Header row
    col_metric, * \
        col_keywords = st.columns([2] + [1] * len(selected_keywords))

    with col_metric:
        st.write("**Metric**")
    for i, kw in enumerate(selected_keywords):
        with col_keywords[i]:
            st.write(f"**{kw}**")

    # Data rows
    for metric_name in metric_names:
        col_metric, * \
            col_values = st.columns([2] + [1] * len(selected_keywords))

        with col_metric:
            st.write(metric_name)

        # Find max value for this metric (for highlighting)
        numeric_values = [metrics_numeric[kw][metric_name]
                            for kw in selected_keywords]
        max_value = max(numeric_values) if numeric_values else None

        for i, kw in enumerate(selected_keywords):
            with col_values[i]:
                value = metrics_data[kw][metric_name]
                numeric_value = metrics_numeric[kw][metric_name]
                col_val, col_symbol = st.columns([1, 3])
                with col_val:
                    st.write(value)
                with col_symbol:
                    if numeric_value == max_value:
                        st.markdown("⭐", text_alignment="left")

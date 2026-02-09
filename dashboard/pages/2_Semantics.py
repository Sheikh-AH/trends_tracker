"""
Home Dashboard - Main visualization page with engaging analytics.
"""

import random
import time
from datetime import datetime, timedelta
from io import BytesIO

import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

# Import shared functions from utils module
import sys
from utils import (
    get_db_connection,
    get_user_keywords,
    get_kpi_metrics_from_db,
    generate_word_cloud_data,
    generate_sentiment_calendar_data,
    generate_trending_velocity,
    generate_network_graph_data,
    get_featured_posts,
    render_sidebar
)
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Home - Trends Tracker",
        page_icon="🏠",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Cached Featured Posts ==============
@st.cache_data(ttl=1800)  # 30 minutes = 1800 seconds
def get_cached_featured_posts(_conn, keyword: str, limit: int = 10) -> list:
    """Fetch featured posts with 30-minute cache TTL.
    
    Args:
        _conn: Database connection (underscore prefix tells Streamlit not to hash it)
        keyword: The keyword to filter posts by
        limit: Number of posts to retrieve (default: 10)
    
    Returns:
        List of featured post dictionaries
    """
    try:
        cursor = _conn.cursor(cursor_factory=RealDictCursor)
        posts = get_featured_posts(cursor, keyword=keyword, limit=limit)
        cursor.close()
        return posts
    except Exception:
        return []


# ============== Visualization Functions ==============
@st.fragment(run_every=10)
def render_typing_animation(selected_keyword: str):
    """Render a featured post with typing animation effect.

    Uses real posts from the database if available.
    """
    st.markdown("### ⌨️ Featured Post")

    # Get cached featured posts (refreshes every 30 minutes)
    conn = st.session_state.db_conn
    featured_posts = get_cached_featured_posts(conn, selected_keyword, limit=10)

    if not featured_posts:
        st.info(f"No posts related to '{selected_keyword}' found yet.")
        return

    # Cycle through featured posts based on current time
    post_index = int(time.time() // 10) % len(featured_posts)
    post = featured_posts[post_index]

    # Display the post with markdown
    st.markdown(f"*{post['post_text']}*")

    # Display post metadata
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        timestamp = post['timestamp']
        if timestamp:
            st.caption(f"**{post['author']}** • {timestamp.strftime('%b %d, %H:%M')}")
        else:
            st.caption(f"**{post['author']}**")
    with col2:
        st.caption(f"❤️ {post['likes']}")
    with col3:
        st.caption(f"🔄 {post['reposts']}")
    with col4:
        st.caption(f"💬 {post['comments']}")


def render_word_cloud(word_data: dict, keyword: str):
    """Render word cloud visualization."""
    st.markdown("### ☁️ Associated Keywords")

    if not word_data:
        st.info("No word data available.")
        return

    # Generate word cloud
    wc = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='viridis',
        max_words=50,
        relative_scaling=0.5
    ).generate_from_frequencies(word_data)

    # Convert to image
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(f'Words associated with "{keyword}"', fontsize=14, pad=10)

    st.pyplot(fig)
    plt.close()


def render_sentiment_calendar(calendar_data: pd.DataFrame, keyword: str):
    """Render sentiment calendar heatmap."""
    st.markdown("### 📅 Sentiment Calendar")

    if calendar_data.empty:
        st.info("No calendar data available.")
        return

    # Create GitHub-style calendar heatmap using Altair
    calendar_data['day_name'] = calendar_data['date'].dt.strftime('%a')
    calendar_data['week_of_year'] = calendar_data['date'].dt.isocalendar().week

    heatmap = alt.Chart(calendar_data).mark_rect(
        cornerRadius=3,
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X('week_of_year:O', title='Week', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('day_name:O',
                title='Day',
                sort=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
        color=alt.Color('sentiment:Q',
                       scale=alt.Scale(scheme='redyellowgreen', domain=[-1, 1]),
                       title='Sentiment'),
        tooltip=[
            alt.Tooltip('date:T', title='Date'),
            alt.Tooltip('sentiment:Q', title='Sentiment', format='.2f'),
            alt.Tooltip('day_name:N', title='Day')
        ]
    ).properties(
        height=200,
        title=f'Daily Sentiment for "{keyword}"'
    )

    st.altair_chart(heatmap, use_container_width=True)


def render_trending_speedometer(velocity_data: dict, keyword: str):
    """Render trending velocity speedometer."""
    st.markdown("### 🚀 Trending Velocity")

    velocity = velocity_data["velocity"]
    direction = velocity_data["direction"]
    percent_change = velocity_data["percent_change"]

    # Color based on direction
    if direction == "accelerating":
        color = "#00CC96"
        icon = "🔥"
    elif direction == "decelerating":
        color = "#EF553B"
        icon = "📉"
    else:
        color = "#636EFA"
        icon = "➡️"

    # Create gauge chart using Altair
    # Arc for background
    background = alt.Chart(pd.DataFrame({'value': [100]})).mark_arc(
        innerRadius=80,
        outerRadius=120,
        theta=3.14159,
        theta2=0,
        color='#e0e0e0'
    )

    # Arc for value
    value_angle = 3.14159 * (1 - velocity / 100)

    gauge_data = pd.DataFrame({
        'value': [velocity],
        'start': [3.14159],
        'end': [value_angle]
    })

    # Display as metric with custom styling
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 30px;
            background: linear-gradient(180deg, {color}22 0%, white 100%);
            border-radius: 20px;
            border: 3px solid {color};
        ">
            <div style="font-size: 4em; margin-bottom: 10px;">{icon}</div>
            <div style="font-size: 3em; font-weight: bold; color: {color};">{velocity}%</div>
            <div style="font-size: 1.2em; text-transform: uppercase; letter-spacing: 2px; color: #666;">
                {direction}
            </div>
            <div style="font-size: 1em; margin-top: 10px; color: #888;">
                {'+' if percent_change > 0 else ''}{percent_change}% vs last period
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_network_graph(graph_data: dict):
    """Render keyword network graph using st-link-analysis with enhanced styling."""
    st.markdown("### 🔗 Keyword Network")

    if not graph_data["nodes"]:
        st.info("Add keywords to see network connections.")
        return

    try:
        from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle

        # Color palettes for variety
        node_colors = ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#00f2fe", "#43e97b", "#fa709a", "#fee140"]
        edge_colors = ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#00f2fe", "#43e97b", "#fa709a", "#fee140"]

        # Prepare nodes and edges for st_link_analysis
        elements = {"nodes": [], "edges": []}

        for idx, node in enumerate(graph_data["nodes"]):
            elements["nodes"].append({
                "data": {
                    "id": node["id"],
                    "label": node["label"],
                    "size": node.get("size", 30),
                    "color": node_colors[idx % len(node_colors)]
                }
            })

        for idx, edge in enumerate(graph_data["edges"]):
            elements["edges"].append({
                "data": {
                    "id": f"{edge['source']}-{edge['target']}",
                    "source": edge["source"],
                    "target": edge["target"],
                    "weight": edge["weight"],
                    "label": str(edge["weight"]),
                    "color": edge_colors[idx % len(edge_colors)]
                }
            })

        # Define node styles with data-driven colors
        node_styles = [
            NodeStyle("default", "data(color)", "label", "circle")
        ]

        # Define edge styles with data-driven colors and labels
        edge_styles = [
            EdgeStyle("default", "data(color)", caption="label", directed=False)
        ]

        # Render the graph
        st_link_analysis(
            elements,
            layout="cose",
            node_styles=node_styles,
            edge_styles=edge_styles,
            height=400
        )

    except ImportError:
        # Fallback visualization if st-link-analysis not installed
        st.warning("Network graph library not installed. Install with: `pip install st-link-analysis`")

        # Show as simple table instead
        if graph_data["edges"]:
            edges_df = pd.DataFrame(graph_data["edges"])
            edges_df.columns = ["From", "To", "Connection Count"]
            st.dataframe(edges_df, use_container_width=True, hide_index=True)


def render_kpi_metrics(metrics: dict):
    """Render KPI metrics row."""
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    with kpi_col1:
        st.metric(
            label="📢 Mentions",
            value=f"{metrics['mentions']:,}",
            delta=f"{metrics.get('mentions_delta', 0)}%"
        )
    with kpi_col2:
        st.metric(
            label="📝 Posts",
            value=f"{metrics['posts']:,}",
            delta=f"{metrics.get('posts_delta', 0)}%"
        )
    with kpi_col3:
        st.metric(
            label="🔄 Reposts",
            value=f"{metrics['reposts']:,}",
            delta=f"{metrics.get('reposts_delta', 0)}%"
        )
    with kpi_col4:
        st.metric(
            label="💬 Comments",
            value=f"{metrics['comments']:,}",
            delta=f"{metrics.get('comments_delta', 0)}%"
        )
    with kpi_col5:
        sentiment_color = "normal" if metrics['avg_sentiment'] >= 0 else "inverse"
        st.metric(
            label="😊 Avg Sentiment",
            value=f"{metrics['avg_sentiment']:.2f}",
            delta=f"{metrics.get('sentiment_delta', 0):.2f}",
            delta_color=sentiment_color
        )


# ============== Main Function ==============

def main():
    """Main function for the Home page."""
    st.title("🏠 Trends Tracker Home")

    # Get connection from session state
    conn = st.session_state.db_conn

    # Load keywords if needed
    if not st.session_state.get("keywords_loaded", False):
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True

    # Top controls
    col1, col2, col3 = st.columns([2, 2, 4])

    with col1:
        keywords = st.session_state.get("keywords", [])
        if keywords:
            selected_keyword = st.selectbox("Select Keyword", options=keywords, index=0)
        else:
            st.warning("No keywords tracked. Add some in Manage Topics.")
            st.write(st.session_state)
            st.stop()

    with col2:
        days_options = {
            "Last 1 day": 1,
            "Last 2 days": 2,
            "Last 3 days": 3,
            "Last 4 days": 4,
            "Last 5 days": 5,
            "Last 6 days": 6,
            "Last 7 days": 7,
            "Last 14 days": 14,
            "Last 30 days": 30,
            "Last 90 days": 90
        }
        selected_period = st.selectbox("Time Period", options=list(days_options.keys()))
        days = days_options[selected_period]

    st.markdown("---")

    # KPI Metrics Row
    metrics = get_kpi_metrics_from_db(conn, selected_keyword, days)
    render_kpi_metrics(metrics)

    st.markdown("---")

    # Featured Post with Typing Animation
    render_typing_animation(selected_keyword)

    st.markdown("---")

    # Word Cloud and Trending Speedometer
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        word_data = generate_word_cloud_data(selected_keyword, days)
        render_word_cloud(word_data, selected_keyword)

    with chart_col2:
        velocity_data = generate_trending_velocity(selected_keyword, days)
        render_trending_speedometer(velocity_data, selected_keyword)

    st.markdown("---")

    # Sentiment Calendar
    calendar_data = generate_sentiment_calendar_data(selected_keyword, days)
    render_sentiment_calendar(calendar_data, selected_keyword)

    st.markdown("---")

    # Keyword Network Graph
    graph_data = generate_network_graph_data(keywords)
    render_network_graph(graph_data)

    # Default Sidebar
    # Render shared sidebar
    render_sidebar()


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
if __name__ == "__main__":
    configure_page()
    main()

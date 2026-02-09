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
    get_user_keywords,
    get_kpi_metrics_from_db,
    get_sentiment_by_day,
    get_featured_posts,
    get_sentiment_emoji,
    get_latest_post_text_corpus,
    extract_keywords_yake,
    diversify_keywords,
    render_sidebar
)
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Semantics",
        page_icon="art/logo_blue.svg",
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
    """Fetch featured posts with 30-minute cache TTL."""
    try:
        cursor = _conn.cursor(cursor_factory=RealDictCursor)
        posts = get_featured_posts(cursor, keyword=keyword, limit=limit)
        cursor.close()
        return posts
    except Exception:
        return []


# ============== Visualization Functions ==============
@st.fragment(run_every=10)
def render_featured_posts(selected_keyword: str):
    """Render a featured post on a styled gradient background.

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

    # Display post on gradient background
    post_link = f'<a href="{post["post_url"]}" target="_blank" style="color: white; text-decoration: none; cursor: pointer;">{post["post_text"]}</a>' if post.get("post_url") else post["post_text"]

    # Create author link with author_url
    author_link = f'<a href="{post["author_url"]}" target="_blank" style="color: white; text-decoration: none; cursor: pointer;"><strong>{post["author"]}</strong></a>' if post.get("author_url") else f"<strong>{post['author']}</strong>"

    # Format timestamp
    timestamp = post.get("timestamp", "")
    if timestamp:
        timestamp_str = timestamp.strftime("%b %d, %H:%M") if hasattr(timestamp, 'strftime') else str(timestamp)[:10]
    else:
        timestamp_str = ""

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
    ">
        <p style="font-size: 1.1em; line-height: 1.6; margin-bottom: 20px;">
            {post_link}
        </p>
        <div style="display: flex; justify-content: space-between; font-size: 0.95em; opacity: 0.95;">
            <span>{author_link}</span>
        </div>
        <div style="display: flex; gap: 20px; margin-top: 15px; font-size: 0.9em; opacity: 0.9; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 20px;">
                <span>❤️ {post.get('likes', 0):,}</span>
                <span>🔄 {post.get('reposts', 0):,}</span>
                <span>💬 {post.get('comments', 0):,}</span>
            </div>
            <span>{timestamp_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def get_keyword_word_cloud_data(_conn, keyword: str, day_limit: int = 7) -> dict:
    """Extract and process keywords for word cloud visualization."""
    # Get post text corpus
    corpus = get_latest_post_text_corpus(_conn, keyword, day_limit=day_limit, post_count_limit=10000)

    if not corpus:
        return {}

    # Extract keywords using YAKE
    raw_keywords = extract_keywords_yake(corpus, num_keywords=100)

    # Diversify to remove redundant terms
    diversified = diversify_keywords(raw_keywords, keyword, max_results=50)

    # Convert to word cloud format (word: frequency)
    # YAKE score is inverse (lower = more relevant), so we invert it
    if not diversified:
        return {}

    word_freq = {}
    for kw in diversified:
        # Invert score: lower YAKE score = higher frequency for word cloud
        # Add small epsilon to avoid division by zero
        inverted_score = 1 / (kw["score"] + 1e-10)
        word_freq[kw["keyword"]] = inverted_score

    return word_freq


def render_word_cloud(keyword: str):
    """Render word cloud visualization using extracted keywords."""
    st.markdown("### ☁️ Associated Keywords")

    conn = st.session_state.db_conn
    word_data = get_keyword_word_cloud_data(conn, keyword)

    if not word_data:
        st.info(f"No associated keywords found for '{keyword}'.")
        return

    # Company color palette (dark blues that stand out on white)
    company_colors = ["#0D3C81", "#0D47A1", "#1565C0", "#1976D2"]

    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        import random
        return random.choice(company_colors)

    # Generate word cloud with improved styling
    wc = WordCloud(
        width=1200,
        height=500,
        background_color='white',
        max_words=40,
        relative_scaling=0.3,
        font_path='/System/Library/Fonts/Supplemental/Arial.ttf',
        prefer_horizontal=0.7,
        min_font_size=12,
        max_font_size=120,
        margin=5,
        collocations=False,
        color_func=color_func
    ).generate_from_frequencies(word_data)

    # Convert to image
    fig, ax = plt.subplots(figsize=(12, 5), facecolor='white')
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_facecolor('white')
    fig.tight_layout(pad=0)

    st.pyplot(fig, transparent=True)
    plt.close()


def render_sentiment_calendar(keyword: str, days: int = 30):
    """Render sentiment calendar heatmap with red-orange-yellow-green gradient."""
    st.markdown("### 📅 Sentiment Calendar")

    conn = st.session_state.db_conn
    sentiment_data = get_sentiment_by_day(conn, keyword, day_limit=days)
    
    if not sentiment_data:
        st.info("No sentiment data available for this period.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(sentiment_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Clamp sentiment to [-0.5, 0.5] range for color mapping
    df['sentiment_clamped'] = df['avg_sentiment'].clip(-0.5, 0.5)
    
    # Add calendar fields
    df['day_name'] = df['date'].dt.strftime('%a')
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.strftime('%b')

    # Create heatmap with red-orange-yellow-green gradient
    heatmap = alt.Chart(df).mark_rect(
        cornerRadius=4,
        stroke='#e0e0e0',
        strokeWidth=1
    ).encode(
        x=alt.X('week_of_year:O', 
                title='Week', 
                axis=alt.Axis(labelAngle=0, labels=False, ticks=False)),
        y=alt.Y('day_name:O',
                title=None,
                sort=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
        color=alt.Color('sentiment_clamped:Q',
                       scale=alt.Scale(
                           domain=[-0.5, -0.25, 0, 0.25, 0.5],
                           range=['#d32f2f', '#ff9800', '#ffeb3b', '#8bc34a', '#4caf50']
                       ),
                       legend=alt.Legend(title='Sentiment')),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%b %d, %Y'),
            alt.Tooltip('avg_sentiment:Q', title='Avg Sentiment', format='.3f'),
            alt.Tooltip('post_count:Q', title='Posts')
        ]
    ).properties(
        height=180
    )

    st.altair_chart(heatmap, use_container_width=True)

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
        sentiment_emoji = get_sentiment_emoji(metrics['avg_sentiment'])
        st.metric(
            label=f"{sentiment_emoji} Avg Sentiment",
            value=f"{metrics['avg_sentiment']:.2f}",
            delta=f"{metrics.get('sentiment_delta', 0):.2f}",
            delta_color=sentiment_color
        )

# ============== Main Function ==============

def main():
    """Main function for the Home page."""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        # Logo and title
        col_img, col_text = st.columns([0.2, 1], gap="small")
        with col_img:
            st.image("art/logo_blue.svg", width=100)
        with col_text:
            st.title("Trendfunnel - Semantics")

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
    render_featured_posts(selected_keyword)

    st.markdown("---")

    # Word Cloud
    render_word_cloud(selected_keyword)

    st.markdown("---")

    # Sentiment Calendar
    render_sentiment_calendar(selected_keyword, days)

    # Render shared sidebar
    render_sidebar()


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
if __name__ == "__main__":
    configure_page()
    main()

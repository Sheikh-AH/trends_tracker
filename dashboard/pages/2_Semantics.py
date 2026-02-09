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
    get_posts_by_date,
    get_featured_posts,
    get_sentiment_emoji,
    get_latest_post_text_corpus,
    extract_keywords_yake,
    diversify_keywords,
    uri_to_url,
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
    """Render sentiment calendar heatmap as a proper monthly calendar grid."""
    st.markdown("### 📅 Sentiment Calendar")

    conn = st.session_state.db_conn

    # Always fetch current month's data
    today = datetime.now().date()
    first_of_month = today.replace(day=1)

    # Get last day of month
    if today.month == 12:
        last_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # Fetch sentiment data for the month
    days_in_month = (last_of_month - first_of_month).days + 1
    sentiment_data = get_sentiment_by_day(conn, keyword, day_limit=days_in_month + (today - first_of_month).days)

    # Create complete date range for the full month
    all_dates = pd.date_range(start=first_of_month, end=last_of_month, freq='D')
    full_df = pd.DataFrame({'date': all_dates})

    # Merge with sentiment data (left join to keep all days)
    if sentiment_data:
        sentiment_df = pd.DataFrame(sentiment_data)
        sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
        df = full_df.merge(sentiment_df, on='date', how='left')
    else:
        df = full_df
        df['avg_sentiment'] = float('nan')
        df['post_count'] = 0

    # Fill NaN for display
    df['post_count'] = df['post_count'].fillna(0).astype(int)
    df['has_data'] = df['avg_sentiment'].notna()
    df['sentiment_clamped'] = df['avg_sentiment'].clip(-0.5, 0.5)

    # Calendar fields - proper grid layout
    df['day_of_week'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['day_name'] = df['date'].dt.strftime('%a')
    df['week_of_month'] = ((df['date'].dt.day - 1) // 7) + 1
    df['day_of_month'] = df['date'].dt.day

    # Adjust week_of_month to account for starting day
    first_day_weekday = first_of_month.weekday()
    df['week_row'] = ((df['date'].dt.day - 1 + first_day_weekday) // 7)

    # Create the calendar heatmap
    heatmap = alt.Chart(df).mark_rect(
        cornerRadius=3,
        stroke='#e0e0e0',
        strokeWidth=1
    ).encode(
        x=alt.X('day_of_week:O',
                title=None,
                axis=alt.Axis(
                    labels=True,
                    labelExpr="['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][datum.value]",
                    labelAngle=0
                )),
        y=alt.Y('week_row:O',
                title=None,
                axis=alt.Axis(labels=False, ticks=False)),
        color=alt.condition(
            'datum.has_data == true',
            alt.Color('sentiment_clamped:Q',
                     scale=alt.Scale(
                         domain=[-0.5, -0.25, 0, 0.25, 0.5],
                         range=['#d32f2f', '#ff9800', '#ffeb3b', '#8bc34a', '#4caf50']
                     ),
                     legend=alt.Legend(title='Sentiment')),
            alt.value('#f5f5f5')
        ),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%b %d, %Y'),
            alt.Tooltip('avg_sentiment:Q', title='Avg Sentiment', format='.3f'),
            alt.Tooltip('post_count:Q', title='Posts')
        ]
    ).properties(
        height=300,
        title=f"{today.strftime('%B %Y')}"
    )

    # Add day labels on each cell
    text = alt.Chart(df).mark_text(
        align='center',
        baseline='middle',
        fontSize=14,
        fontWeight='bold'
    ).encode(
        x=alt.X('day_of_week:O'),
        y=alt.Y('week_row:O'),
        text='day_of_month:Q',
        color=alt.condition(
            'datum.has_data == true',
            alt.value('#333333'),
            alt.value('#999999')
        )
    )

    st.altair_chart(heatmap + text, use_container_width=True)


@st.cache_data(ttl=1800)  # 30 minutes
def get_cached_posts_by_date(_conn, keyword: str, date_str: str, limit: int = 10) -> list:
    """Cached wrapper for fetching posts by date."""
    from datetime import datetime
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    return get_posts_by_date(_conn, keyword, date_obj, limit)


def render_day_posts(keyword: str):
    """Render posts for a selected date."""
    st.markdown("### 📋 Posts by Date")

    conn = st.session_state.db_conn
    today = datetime.now().date()
    first_of_month = today.replace(day=1)

    # Date picker constrained to current month
    selected_date = st.date_input(
        "Select a date",
        value=today,
        min_value=first_of_month,
        max_value=today,
        key="post_seeker_date"
    )

    if selected_date:
        date_str = selected_date.strftime("%Y-%m-%d")
        posts = get_cached_posts_by_date(conn, keyword, date_str, limit=10)

        if posts:
            st.markdown(f"**Showing {len(posts)} random posts from {selected_date.strftime('%B %d, %Y')}:**")

            for post in posts:
                sentiment_raw = post.get('sentiment_score', 0)
                try:
                    sentiment = float(sentiment_raw) if sentiment_raw is not None else 0.0
                except (ValueError, TypeError):
                    sentiment = 0.0
                emoji = get_sentiment_emoji(sentiment)
                text = post.get('text', '')
                author_did = post.get('author_did', '')
                post_uri = post.get('post_uri', '')
                posted_at = post.get('posted_at')

                # Format timestamp
                if posted_at:
                    if hasattr(posted_at, 'strftime'):
                        time_str = posted_at.strftime('%I:%M %p')
                    else:
                        time_str = str(posted_at)
                else:
                    time_str = ''

                # Get post URL
                post_url = uri_to_url(post_uri) if post_uri else ''

                # Truncate author DID for display
                author_display = f"@{author_did[:20]}..." if len(author_did) > 20 else f"@{author_did}"

                # Render post card
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        padding: 15px;
                        border-radius: 10px;
                        margin-bottom: 10px;
                        border-left: 4px solid #0D47A1;
                    ">
                        <p style="margin-bottom: 8px; font-size: 14px;">{text}</p>
                        <div style="font-size: 12px; color: #666;">
                            {author_display} • {time_str} • {emoji} {sentiment:.2f}
                            {f' • <a href="{post_url}" target="_blank">View Post</a>' if post_url else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"No posts found for {selected_date.strftime('%B %d, %Y')}")


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

    st.markdown("---")

    # Post Seeker
    render_day_posts(selected_keyword)

    # Render shared sidebar
    render_sidebar()


# ============== Entry Point ==============
# Streamlit pages are executed as modules, so we run at module level
if __name__ == "__main__":
    configure_page()
    main()

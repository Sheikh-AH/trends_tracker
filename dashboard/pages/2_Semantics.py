"""Home Dashboard - Main visualization page with engaging analytics."""

from streamlit_echarts import st_echarts
import math
from datetime import datetime, timedelta
import altair as alt
import pandas as pd
import streamlit as st

from utils import (
    get_user_keywords,
    get_sentiment_by_day,
    get_latest_post_text_corpus,
    extract_keywords_yake,
    diversify_keywords,
    render_sidebar,
    _load_sql_query
)
from psycopg2.extras import RealDictCursor


def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Semantics",
        page_icon="art/logo_blue.svg",
        layout="wide"
    )

    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ---------- DATA ----------

def get_avg_sentiment_by_phrase(conn, target_keyword: str, phrases: list[str], day_limit: int):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = _load_sql_query("get_phrase_avg_sentiment.sql")
    results = {}
    for phrase in phrases:
        cursor.execute(
            query, (target_keyword, f"{day_limit} days", f"%{phrase}%"))
        row = cursor.fetchone()
        results[phrase] = {
            "avg_sentiment": row["avg_sentiment"],
            "post_count": row["post_count"],
        }
    cursor.close()
    return results


@st.cache_data(ttl=3600)
def get_keyword_word_cloud_data(_conn, keyword: str, day_limit: int = 7) -> dict:
    corpus = get_latest_post_text_corpus(
        _conn, keyword, day_limit=day_limit, post_count_limit=10000)
    if not corpus:
        return {}
    raw_keywords = extract_keywords_yake(corpus, num_keywords=100)
    diversified = diversify_keywords(raw_keywords, keyword, max_results=50)
    if not diversified:
        return {}
    phrases = [kw["keyword"] for kw in diversified]
    sentiment_by_phrase = get_avg_sentiment_by_phrase(
        _conn, keyword, phrases[:10], day_limit)
    return {
        kw["keyword"]: {
            "weight": 1 / (kw["score"] + 1e-10),
            "avg_sentiment": sentiment_by_phrase.get(kw["keyword"], {}).get("avg_sentiment"),
            "post_count": sentiment_by_phrase.get(kw["keyword"], {}).get("post_count"),
        }
        for kw in diversified
    }


# ---------- HELPERS ----------

def normalize_word_freq(word_data: dict) -> dict:
    return {k: {**v, "weight": math.log(v["weight"] + 1)} for k, v in word_data.items()}


def to_echarts_wordcloud(word_data: dict):
    return [{"name": k, "value": float(v["weight"])} for k, v in word_data.items()]


def get_top_n_words(word_data: dict, n: int = 10):
    return sorted(word_data.items(), key=lambda x: x[1]["weight"], reverse=True)[:n]


# ---------- RENDER ----------

def render_wordcloud(word_data: dict):
    if not word_data:
        st.info("No data available for word cloud")
        return
    word_data = normalize_word_freq(word_data)
    is_dark_mode = st.get_option("theme.base") == "dark"
    text_color = "#9BB7E0" if is_dark_mode else "#0D3C81"
    col_table, col_cloud = st.columns([1, 2])

    with col_table:
        if not word_data:
            st.warning("All words removed.")
            return
        st.subheader("Top 10 Keywords")
        top_words = get_top_n_words(word_data, n=10)
        st.dataframe(
            [
                {
                    "Word": w,
                    "Weight": round(v["weight"], 2),
                    "Posts": v["post_count"],
                }
                for w, v in top_words
            ],
            hide_index=True,
            use_container_width=True,
        )

    option = {
        "tooltip": {"show": True},
        "series": [{
            "type": "wordCloud",
            "shape": "circle",
            "gridSize": 8,
            "sizeRange": [14, 70],
            "rotationRange": [-45, 45],
            "textStyle": {"color": text_color, "fontWeight": "bold"},
            "data": to_echarts_wordcloud(word_data),
        }]
    }
    with col_cloud:
        st_echarts(option, height="500px")


def render_sentiment_calendar(keyword: str, days: int = 30):
    """Render sentiment calendar with best/worst day metrics."""
    st.markdown("## 📅 Sentiment Calendar")
    conn = st.session_state.db_conn
    today = datetime.now().date()
    first_of_month = today.replace(day=1)
    last_of_month = (today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                     if today.month < 12 else today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1))
    days_in_month = (last_of_month - first_of_month).days + 1
    sentiment_data = get_sentiment_by_day(
        conn, keyword, day_limit=days_in_month + (today - first_of_month).days)

    all_dates = pd.date_range(start=first_of_month,
                              end=last_of_month, freq='D')
    full_df = pd.DataFrame({'date': all_dates})
    if sentiment_data:
        sentiment_df = pd.DataFrame(sentiment_data)
        sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
        df = full_df.merge(sentiment_df, on='date', how='left')
    else:
        df = full_df.copy()
        df['avg_sentiment'] = float('nan')
        df['post_count'] = 0

    df['post_count'] = df['post_count'].fillna(0).astype(int)
    df['has_data'] = df['avg_sentiment'].notna()
    df['sentiment_clamped'] = df['avg_sentiment'].clip(-0.5, 0.5)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    first_day_weekday = first_of_month.weekday()
    df['week_row'] = ((df['date'].dt.day - 1 + first_day_weekday) // 7)

    # Columns: calendar left, metrics right
    col_calendar, col_space, col_metrics = st.columns([16, 1, 3])

    # Calendar
    heatmap = alt.Chart(df).mark_rect(cornerRadius=3, stroke='#e0e0e0', strokeWidth=1).encode(
        x=alt.X('day_of_week:O',
                title=None,
                axis=alt.Axis(labels=True, labelExpr="['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][datum.value]", labelAngle=0)),
        y=alt.Y('week_row:O', title=None, axis=alt.Axis(
            labels=False, ticks=False)),
        color=alt.condition(
            'datum.has_data == true',
            alt.Color('sentiment_clamped:Q',
                      scale=alt.Scale(domain=[-0.5, -0.25, 0, 0.25, 0.5],
                                      range=['#d32f2f', '#ff9800', '#ffeb3b', '#8bc34a', '#4caf50']),
                      legend=alt.Legend(title='Sentiment')),
            alt.value('#f5f5f5')
        ),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%b %d, %Y'),
            alt.Tooltip('avg_sentiment:Q',
                        title='Avg Sentiment', format='.3f'),
            alt.Tooltip('post_count:Q', title='Posts')
        ]
    ).properties(height=300, title=f"{today.strftime('%B %Y')}")
    text = alt.Chart(df).mark_text(align='center', baseline='middle', fontSize=14, fontWeight='bold').encode(
        x='day_of_week:O', y='week_row:O', text='day_of_month:Q',
        color=alt.condition('datum.has_data == true',
                            alt.value('#333333'), alt.value('#999999'))
    )
    with col_calendar:
        st.altair_chart(heatmap + text, use_container_width=True)

    # Metrics
    with col_metrics:
        df_metrics = df[df['has_data']].copy()
        if not df_metrics.empty:
            best_day_row = df_metrics.loc[df_metrics['avg_sentiment'].idxmax()]
            worst_day_row = df_metrics.loc[df_metrics['avg_sentiment'].idxmin(
            )]
            st.metric("Best Day", f"{best_day_row['date'].strftime('%b %d')}", round(
                best_day_row['avg_sentiment'], 3))
            st.metric("Worst Day", f"{worst_day_row['date'].strftime('%b %d')}", round(
                worst_day_row['avg_sentiment'], 3))
        else:
            st.info("No sentiment data this month.")

def load_keywords(conn) -> list:
    """Check for user keywords and load them into session state."""

    if not st.session_state.get("keywords_loaded", False):
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True

    keywords = st.session_state.get("keywords", [])
    if not keywords:
        st.warning("No keywords tracked. Add some in Manage Topics.")
        st.write(st.session_state)
        st.stop()
    
    return keywords


if __name__ == "__main__":
    configure_page()
    render_sidebar()

    col_title, col_keyword, col_period, col_remove = st.columns([3, 2, 2, 2])
    with col_title:
        st.markdown("## ☁️ Semantic Cloud")

    conn = st.session_state.db_conn

    keywords = load_keywords(conn)
    with col_keyword:
        selected_keyword = st.selectbox(
            "Select Keyword", options=keywords, index=0)
    
    days_options = {"Last 1 day": 1, "Last 3 days": 3, "Last 7 days": 7,
                    "Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}
    with col_period:
        selected_period = st.selectbox("Time Period", 
                                       options=list(days_options.keys()))
        days = days_options[selected_period]

    word_freq = get_keyword_word_cloud_data(conn, selected_keyword, days)
    with col_remove:
        removed_words = st.multiselect("Remove words from analysis", 
                                       options=sorted(word_freq.keys()))
    filtered_word_freq = {k: v for k,v in word_freq.items() if k not in removed_words}
    
    render_wordcloud(filtered_word_freq)
    render_sentiment_calendar(selected_keyword, days)
    st.markdown("---")

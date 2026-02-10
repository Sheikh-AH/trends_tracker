"""AI Insights - LLM-generated summaries and recommendations for keywords."""

import os
from time import sleep
import streamlit as st
from dotenv import load_dotenv
from psycopg2 import connect
from pandas import read_sql
import matplotlib.pyplot as plt
from utils import (
    get_db_connection,
    render_sidebar,
    _load_sql_query
)

def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="AI Insights - Trends Tracker",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()

@st.cache_data(ttl=3600)
def get_summary(_conn):
    """Fetch the latest summary and insights for the user."""
    with _conn.cursor() as cursor:
        cursor.execute("""
            SELECT summary
            FROM llm_summary
            WHERE user_id = %s
            ORDER BY summary_id DESC
            LIMIT 1;
        """, (st.session_state.user_id,))
        result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return "No summary available."


def stream_summary(summary):
    """Stream the summary text to the UI."""
    for word in summary.split(" "):
        yield word + " "
        sleep(0.01)

@st.cache_data(ttl=3600)
def get_user_posts(_conn, user_id: int) -> list:
    """Retrieve all keywords for a user."""
    query = _load_sql_query("queries/user_posts.sql")
    return read_sql(query, _conn, params=(user_id,))

@st.cache_data(ttl=3600)
def gen_keyword_graphic(_conn, user_id: int):
    """Generate donut charts for each keyword showing post type proportions and sentiment."""
    user_posts = get_user_posts(_conn, user_id)

    if user_posts.empty:
        st.info("No posts found for your tracked keywords in the last 24 hours.")
        return

    cols = st.columns(5)

    for idx, row in user_posts.iterrows():
        col_idx = idx % 5
        with cols[col_idx]:
            # Data for the donut
            proportions = [
                row['original_post_proportion'] or 0,
                row['repost_proportion'] or 0,
                row['reply_proportion'] or 0
            ]
            sentiments = [
                row['original_post_sentiment'] or 0.5,
                row['repost_sentiment'] or 0.5,
                row['reply_sentiment'] or 0.5
            ]
            labels = ['Posts', 'Reposts', 'Replies']
            colors = ['#1e3a5f', '#EF553B', '#00CC96']

            widths = [0.15 + 0.45 * ((s + 1) / 2) for s in sentiments]

            fig, ax = plt.subplots(figsize=(3.5, 3.5))
            fig.patch.set_alpha(0)
            ax.set_facecolor('none')
            fig.subplots_adjust(left=-0.1, right=1.1, top=1.1, bottom=-0.1)

            # Only plot if there's data
            if sum(proportions) > 0:
                # Create wedges with varying widths
                theta1 = 0
                for i, (prop, width, color, label) in enumerate(zip(proportions, widths, colors, labels)):
                    if prop > 0:
                        theta2 = theta1 + prop * 360
                        # Create a wedge
                        wedge = plt.matplotlib.patches.Wedge(
                            center=(0, 0),
                            r=1,
                            theta1=theta1,
                            theta2=theta2,
                            width=width,
                            facecolor=color,
                            edgecolor='none',
                            linewidth=0,
                            label=f'{label}: {prop*100:.1f}%'
                        )
                        ax.add_patch(wedge)
                        theta1 = theta2

                # Add grey background circle in center
                center_circle = plt.matplotlib.patches.Circle(
                    xy=(0, 0),
                    radius=0.35,
                    facecolor='#d4d4d4',
                    edgecolor='none'
                )
                ax.add_patch(center_circle)

                ax.set_xlim(-1.2, 1.2)
                ax.set_ylim(-1.2, 1.2)
                ax.set_aspect('equal')
                ax.axis('off')

                # Add total count in center with better readability
                ax.text(0, 0.05, f"{int(row['post_count'])}",
                        ha='center', va='center', fontsize=18, fontweight='bold', color='#000000')
                ax.text(0, -0.15, 'total', ha='center', va='center',
                        fontsize=11, fontweight='bold', color='#666666')

            st.pyplot(fig, transparent=True)
            plt.close(fig)

            # Add badges as legend with proportions below chart
            badge_html = "<div style='display: flex; gap: 8px; align-items: center; justify-content: center; margin-top: 0px;'>"
            for label, prop, color in zip(labels, proportions, colors):
                if prop > 0:
                    badge_html += f"<span style='background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3); color: white; border: 2px solid {color}; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;'>{label}: {prop*100:.1f}%</span>"
            badge_html += "</div>"
            st.markdown(badge_html, unsafe_allow_html=True)

            # Keyword label beneath the graphic
            st.markdown(
                f"<p style='text-align: center; font-weight: bold; font-size: 14px; margin-top: 12px;'>{row['keyword_value']}</p>", unsafe_allow_html=True)


if __name__ == "__main__":

    load_dotenv()
    configure_page()
    render_sidebar()
    conn = get_db_connection()

    st.title("Daily Summary & Insights")
    st.markdown("AI-powered analysis for your tracked keywords.")
    st.divider()
    
    summary = get_summary(conn)
    st.subheader("Latest AI Summary")
    st.write_stream(stream_summary(summary))
    st.divider()
    st.subheader("Keyword Activity")
    gen_keyword_graphic(conn, st.session_state.user_id)

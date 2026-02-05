"""AI Insights - LLM-generated summaries and recommendations for keywords."""

import os
from time import sleep
import streamlit as st
from dotenv import load_dotenv
from psycopg2 import connect
from pandas import DataFrame, read_sql
import matplotlib.pyplot as plt
import numpy as np

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return connect(
        dbname= os.getenv('DB_NAME'),
        user= os.getenv('DB_USER'),
        password= os.getenv('DB_PASSWORD'),
        host= os.getenv('DB_HOST'),
        port= os.getenv('DB_PORT')
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

def gen_sidebar():
    """Generate the sidebar with user info and quick stats."""
    st.sidebar.markdown(f"### 👋 Hello, {st.session_state.get('username', 'User')}!")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Quick Stats")
    st.sidebar.metric("Keywords Tracked", len(st.session_state.get("keywords", [])))
    st.sidebar.metric("Alerts Enabled", "Yes" if st.session_state.get("alerts_enabled", False) else "No")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_id = None
        st.switch_page("app.py")
    st.sidebar.markdown("---")
    st.sidebar.caption("Trends Tracker v1.0")

def get_summary(conn):
    """Fetch the latest summary and insights for the user."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT summary
            FROM llm_summary
            WHERE user_id = %s;
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

def get_query_from_file(filename: str) -> str:
    """Read a SQL query from a file."""
    with open(filename, "r") as file:
        return file.read()
    
def get_user_posts(conn, user_id: int) -> list:
    """Retrieve all keywords for a user."""
    query = get_query_from_file("queries/user_posts.sql")
    return read_sql(query, conn, params=(user_id,))

def gen_keyword_graphic(conn, user_id: int):
    """Generate donut charts for each keyword showing post type proportions and sentiment."""
    user_posts = get_user_posts(conn, user_id)
    
    if user_posts.empty:
        st.info("No posts found for your tracked keywords in the last 24 hours.")
        return
    
    # Create fixed 5 columns for the donut charts (leaves room for future keywords)
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
            
            # Normalize sentiments to width (0.15 to 0.6 range for visibility)
            # Sentiment ranges from -1 to 1, normalize to 0.15-0.6
            # Wider range makes differences more visible
            widths = [0.15 + 0.45 * ((s + 1) / 2) for s in sentiments]
            
            # Create the donut chart with transparent background
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
                ax.text(0, -0.15, 'total', ha='center', va='center', fontsize=11, fontweight='bold', color='#666666')
            
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
            st.markdown(f"<p style='text-align: center; font-weight: bold; font-size: 14px; margin-top: 12px;'>{row['keyword_value']}</p>", unsafe_allow_html=True)
    


if __name__ == "__main__":

    load_dotenv()
    conn = get_db_connection()
    configure_page()

    st.title("Daily Summary & Insights")
    st.markdown("AI-powered analysis for your tracked keywords.")
    st.divider()
    gen_sidebar()

    summary = get_summary(conn)
    st.subheader("Latest AI Summary")
    st.write_stream(stream_summary(summary))
    st.divider()
    st.subheader("Keyword Activity")
    gen_keyword_graphic(conn, st.session_state.user_id)
    



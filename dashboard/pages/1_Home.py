"""
Home - Welcome and introduction page for Trendfunnel.
"""

import random
from datetime import datetime, timedelta
import streamlit as st
import altair as alt
import pandas as pd

# Import shared functions from utils module
import sys
sys.path.insert(0, '..')
from utils import get_db_connection, get_user_keywords
from psycopg2.extras import RealDictCursor


# ============== Page Configuration ==============
def configure_page():
    """Configure page settings and check authentication."""
    st.set_page_config(
        page_title="Trendfunnel",
        page_icon="art/logo_blue.svg",
        layout="wide"
    )

    # Check authentication
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("Please login to access this page.")
        st.switch_page("app.py")
        st.stop()


# ============== Hide Sidebar ==============
def hide_sidebar():
    """Hide the sidebar on this page."""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Google Trends inspired minimal styling */
            .main {
                background-color: #ffffff;
            }
            h1, h2, h3 {
                font-weight: 400;
                color: #202124;
            }
            .stButton button {
                border-radius: 4px;
                font-weight: 500;
                text-transform: none;
            }
        </style>
    """, unsafe_allow_html=True)


# ============== Load Keywords ==============
def load_keywords():
    """Load user keywords from database."""
    if not st.session_state.get("keywords_loaded", False):
        conn = get_db_connection()
        if conn and st.session_state.get("user_id"):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            db_keywords = get_user_keywords(cursor, st.session_state.user_id)
            cursor.close()
            st.session_state.keywords = db_keywords if db_keywords else []
            st.session_state.keywords_loaded = True


# ============== Generate Trending Line Chart ==============
def generate_trending_chart():
    """Generate an animated trending line chart like Google Trends."""
    # Dummy keywords for demo
    keywords = ["AI", "Climate", "Tech", "Travel", "Food"]

    # Generate time series data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')

    data = []
    for keyword in keywords:
        random.seed(hash(keyword))
        base = random.randint(20, 80)
        for i, date in enumerate(dates):
            # Add some variance to make it look realistic
            value = base + random.randint(-15, 15) + (i * random.uniform(-1, 2))
            data.append({
                'Date': date,
                'Keyword': keyword,
                'Interest': max(0, min(100, value))
            })

    df = pd.DataFrame(data)

    # Create Altair chart with Google Trends styling
    chart = alt.Chart(df).mark_line(point=False, strokeWidth=2).encode(
        x=alt.X('Date:T',
                axis=alt.Axis(
                    title=None,
                    labelAngle=0,
                    format='%b %d',
                    grid=False,
                    labelColor='#5f6368',
                    tickColor='#dadce0'
                )),
        y=alt.Y('Interest:Q',
                axis=alt.Axis(
                    title=None,
                    grid=True,
                    gridColor='#f1f3f4',
                    labelColor='#5f6368',
                    tickColor='#dadce0'
                ),
                scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Keyword:N',
                       scale=alt.Scale(
                           range=['#1a73e8', '#ea4335', '#fbbc04', '#34a853', '#ff6d01']
                       ),
                       legend=alt.Legend(
                           orient='top',
                           direction='horizontal',
                           title=None,
                           labelColor='#5f6368'
                       )),
        tooltip=['Keyword:N', 'Date:T', 'Interest:Q']
    ).properties(
        height=300,
        width='container'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        domainColor='#dadce0'
    )

    return chart


# ============== Main Function ==============
def main():
    """Main function for the Welcome page."""
    hide_sidebar()

    # Hero section with logo and branding
    col_logo, col_text = st.columns([1, 4])

    with col_logo:
        st.image("art/logo_blue.svg", width=120)

    with col_text:
        st.markdown("""
        <div style="padding-top: 20px;">
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 400; color: #202124;">
                Trendfunnel
            </h1>
            <p style="margin: 5px 0 0 0; font-size: 1.1rem; color: #5f6368; font-weight: 300;">
                Turning fuzz into bizz
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Trending chart visualization
    st.altair_chart(generate_trending_chart(), use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Load keywords to check if user has set them up
    load_keywords()
    has_keywords = len(st.session_state.get("keywords", [])) > 0

    # Getting Started section - Vertical layout
    st.markdown("""
    <h2 style="font-weight: 400; color: #202124; margin-bottom: 10px;">
        Explore your trends
    </h2>
    """, unsafe_allow_html=True)

    # Vertical button layout
    st.markdown("<br>", unsafe_allow_html=True)

    # Manage Topics Button (always available)
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        st.markdown("""
        <div style="text-align: left; margin-bottom: 20px;">
            <h3 style="font-weight: 400; color: #202124; font-size: 1.1rem; margin-bottom: 5px;">
                📝 Manage Topics
            </h3>
            <p style="color: #5f6368; margin: 0 0 10px 0;">
                Add keywords and topics you want to track
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Set up keywords", type="primary", use_container_width=True, key="manage_topics"):
            st.switch_page("pages/5_Manage_Topics.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # Semantics Button
    with col2:
        st.markdown("""
        <div style="text-align: left; margin-bottom: 20px;">
            <h3 style="font-weight: 400; color: #202124; font-size: 1.1rem; margin-bottom: 5px;">
                📊 Semantics Dashboard
            </h3>
            <p style="color: #5f6368; margin: 0 0 10px 0;">
                Visualize trends with interactive charts and word clouds
            </p>
        </div>
        """, unsafe_allow_html=True)
        if has_keywords:
            if st.button("View trends", use_container_width=True, key="semantics"):
                st.switch_page("pages/2_Semantics.py")
        else:
            st.button("View trends", disabled=True, use_container_width=True, key="semantics_disabled")
            st.caption("⚠️ Add keywords first")

    st.markdown("<br>", unsafe_allow_html=True)

    # Deep Dive Button
    with col2:
        st.markdown("""
        <div style="text-align: left; margin-bottom: 20px;">
            <h3 style="font-weight: 400; color: #202124; font-size: 1.1rem; margin-bottom: 5px;">
                🔍 Keyword Deep Dive
            </h3>
            <p style="color: #5f6368; margin: 0 0 10px 0;">
                Detailed analytics for individual keywords
            </p>
        </div>
        """, unsafe_allow_html=True)
        if has_keywords:
            if st.button("Analyze keywords", use_container_width=True, key="deepdive"):
                st.switch_page("pages/3_Keyword_Deep_Dive.py")
        else:
            st.button("Analyze keywords", disabled=True, use_container_width=True, key="deepdive_disabled")
            st.caption("⚠️ Add keywords first")

    st.markdown("<br>", unsafe_allow_html=True)

    # AI Insights Button
    with col2:
        st.markdown("""
        <div style="text-align: left; margin-bottom: 20px;">
            <h3 style="font-weight: 400; color: #202124; font-size: 1.1rem; margin-bottom: 5px;">
                🤖 AI Insights
            </h3>
            <p style="color: #5f6368; margin: 0 0 10px 0;">
                AI-powered analysis and recommendations
            </p>
        </div>
        """, unsafe_allow_html=True)
        if has_keywords:
            if st.button("Get insights", use_container_width=True, key="ai"):
                st.switch_page("pages/4_AI_Insights.py")
        else:
            st.button("Get insights", disabled=True, use_container_width=True, key="ai_disabled")
            st.caption("⚠️ Add keywords first")

    # Status indicator at bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
    if has_keywords:
        keywords_text = ", ".join(st.session_state.keywords)
        st.markdown(f"""
        <div style="text-align: center; color: #5f6368; padding: 20px;">
            <p style="margin: 0;">Currently tracking: <strong>{keywords_text}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; color: #5f6368; padding: 20px;">
            <p style="margin: 0;">👉 Get started by setting up your first keywords</p>
        </div>
        """, unsafe_allow_html=True)


# ============== Entry Point ==============
configure_page()
main()

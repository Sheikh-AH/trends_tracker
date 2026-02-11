"""UI helper functions for rendering components and templates."""

import logging
import os

import streamlit as st

logger = logging.getLogger(__name__)


def render_sidebar():
    """Render the standard sidebar across all pages."""
    with st.sidebar:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_id = None
            st.rerun()


@st.cache_data(ttl=3600)
def get_sentiment_emoji(sentiment_score: float) -> str:
    """Get emoji based on sentiment score with gradient smileys."""
    if sentiment_score >= 0.4:
        return "😄"  # Grinning
    elif sentiment_score >= 0.25:
        return "😊"  # Smiling
    elif sentiment_score >= 0.1:
        return "🙂"  # Slightly smiling
    elif sentiment_score >= -0.1:
        return "😐"  # Neutral
    elif sentiment_score >= -0.25:
        return "😕"  # Slightly frowning
    elif sentiment_score >= -0.4:
        return "😔"  # Frowning
    else:
        return "😠"  # Angry


# HTML Template cache
_HTML_TEMPLATE_CACHE = {}


@st.cache_data(ttl=3600)
def load_html_template(filepath: str) -> str:
    """Load HTML template from file, with caching."""
    if filepath not in _HTML_TEMPLATE_CACHE:
        try:
            with open(filepath, 'r') as f:
                _HTML_TEMPLATE_CACHE[filepath] = f.read()
        except FileNotFoundError:
            logger.error(f"HTML template not found: {filepath}")
            return ""
    return _HTML_TEMPLATE_CACHE[filepath]

"""Extract and filter posts from Bluesky Jetstream matching specified keywords."""

import sys
import json
import re
import time
from typing import Optional, Callable
from os import _Environ
from pathlib import Path

import websocket

# Add load directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "load"))

from bs_load import get_db_connection


URI = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"


def get_keywords(config: _Environ):
    """Get keywords from database."""
    conn = get_db_connection(config)
    with conn.cursor() as cursor:
        cursor.execute("SELECT keyword_value FROM keywords")
        rows = cursor.fetchall()
    conn.close()
    if not rows:
        return set()
    return {row[0] for row in rows}


def stream_messages():
    """Generator yielding messages continuously from Bluesky Jetstream."""
    ws = websocket.create_connection(URI)
    try:
        while True:
            message = ws.recv()
            yield json.loads(message)
    finally:
        ws.close()


def compile_keyword_patterns(keywords: set) -> dict:
    """Pre-compile regex patterns for all keywords."""
    compiled = {}
    for keyword in keywords:
        keyword_lower = keyword.lower()
        pattern = r"(?:^|\W)" + re.escape(keyword_lower) + r"\w{0,3}(?:\W|$)"
        compiled[keyword] = re.compile(pattern)
    return compiled


def keyword_match(compiled_patterns: dict, post_text: str) -> Optional[set]:
    """Return a set of keywords that match as whole words in post_text using pre-compiled regex"""
    if not compiled_patterns or not post_text:
        return None

    matching = set()
    text_lower = post_text.lower()

    for keyword, pattern in compiled_patterns.items():
        if pattern.search(text_lower):
            matching.add(keyword)

    return matching if matching else None


def stream_filtered_messages(keyword_fetcher: Callable[[], set]):
    """Stream only messages with posts matching keywords."""

    keywords = keyword_fetcher()
    compiled_patterns = compile_keyword_patterns(keywords)
    last_refresh = time.time()
    refresh_interval = 60

    for msg in stream_messages():
        # Refresh keywords periodically
        current_time = time.time()
        if current_time - last_refresh >= refresh_interval:
            new_keywords = keyword_fetcher()
            if new_keywords != keywords:
                keywords = new_keywords
                compiled_patterns = compile_keyword_patterns(keywords)
            last_refresh = current_time

        if msg.get("kind") != "commit":
            continue

        post_text = msg.get("commit", {}).get("record", {}).get("text", "")
        matching_kws = keyword_match(compiled_patterns, post_text)

        if matching_kws:
            msg["matching_keywords"] = list(matching_kws)
            yield msg


if __name__ == "__main__":
    pass

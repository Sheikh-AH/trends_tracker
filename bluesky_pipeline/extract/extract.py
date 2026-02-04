"""
Extract and filter posts from Bluesky Jetstream matching specified keywords.

Provides functions for:
    - Streaming messages from Bluesky Jetstream
    - Filtering posts by keyword matching
"""

import json
import re
import time
from typing import Optional, Callable
from os import _Environ

import websocket

from load.bs_load import get_db_connection


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


def keyword_match(keywords: set, post_text: str) -> Optional[set]:
    """Return a set of keywords that match as whole words in post_text using regex"""
    if not keywords or not post_text:
        return None

    matching = set()
    text_lower = post_text.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Match keyword as a prefix of a word (e.g., 'plant' matches 'plants', 'planting')
        pattern = r"(?:^|\W)" + re.escape(keyword_lower) + r"\w{0,3}(?:\W|$)"
        if re.search(pattern, text_lower):
            matching.add(keyword)

    return matching if matching else None


def stream_filtered_messages(keyword_fetcher: Callable[[], set], refresh_interval: int = 60):
    """Stream only messages with posts matching keywords.

    Args:
        keyword_fetcher: A callable that returns the current set of keywords.
        refresh_interval: How often (in seconds) to refresh keywords from the database.
    """
    keywords = keyword_fetcher()
    last_refresh = time.time()
    print(f"Starting with keywords: {keywords}")

    for msg in stream_messages():
        # Refresh keywords periodically
        current_time = time.time()
        if current_time - last_refresh >= refresh_interval:
            new_keywords = keyword_fetcher()
            if new_keywords != keywords:
                print(f"Keywords updated: {keywords} -> {new_keywords}")
                keywords = new_keywords
            last_refresh = current_time

        if msg.get("kind") != "commit":
            continue
        post_text = msg.get("commit", {}).get("record", {}).get("text", "")
        matching_kws = keyword_match(keywords, post_text)

        if matching_kws:
            msg["matching_keywords"] = list(matching_kws)
            yield msg


if __name__ == "__main__":
    trending_keywords = {"cat"}

    for message in stream_filtered_messages(trending_keywords):
        print(message)

"""
Extract and filter posts from Bluesky Jetstream matching specified keywords.

Provides functions for:
    - Streaming messages from Bluesky Jetstream
    - Filtering posts by keyword matching
"""

import json
import re
from typing import Optional

import websocket


URI = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"


def stream_messages(uri: str = URI):
    """Generator yielding messages continuously from Bluesky Jetstream."""
    ws = websocket.create_connection(uri)
    try:
        while True:
            try:
                message = ws.recv()
                yield json.loads(message)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
    finally:
        ws.close()


def extract_post_text(message: dict) -> str:
    """Extract post text from a Bluesky message."""
    try:
        return message.get("commit", {}).get("record", {}).get("text", "")
    except (KeyError, TypeError):
        return ""


def keyword_match(keywords: set, post_text: str) -> Optional[set]:
    """Return a set of keywords that match as whole words in post_text using regex"""
    if not keywords or not post_text:
        return None

    matching = set()
    text_lower = post_text.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Match keyword as a prefix of a word (e.g., 'plant' matches 'plants', 'planting')
        pattern = r"(?:^|\W)" + re.escape(keyword_lower) + r"\w*"
        if re.search(pattern, text_lower):
            matching.add(keyword)

    return matching if matching else None


def stream_filtered_messages(keywords: set, uri: str = URI):
    """Stream only messages with posts matching keywords."""
    for msg in stream_messages(uri):
        post_text = extract_post_text(msg)
        matching_kws = keyword_match(keywords, post_text)

        if matching_kws:
            msg["matching_keywords"] = list(matching_kws)
            yield msg


if __name__ == "__main__":
    trending_keywords = {"cat"}

    for message in stream_filtered_messages(trending_keywords):
        print(message)
        break

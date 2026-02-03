"""
Extract and filter posts from Bluesky Jetstream matching specified keywords.

Provides utilities for:
    - Database connection management (AWS RDS)
    - Keyword list retrieval from database
    - Jetstream message extraction and filtering
    - Post type classification (post/reply/comment)
    - Post URL composition
"""

import asyncio
import json
import os
import re
from typing import Optional

import psycopg2
import websockets


URI = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"


class BlueskyFirehose:
    """
    Manages persistent Bluesky Jetstream connection. This firehose needs
    websocket connections and a bunch of complex async functions. Therefore
    an object is defined for easier transition into the main pipeline.
    """

    def __init__(self, uri: str = URI):
        """Initialize the firehose connection manager.

        Args:
            uri: Bluesky Jetstream URI (defaults to app.bsky.feed.post collection)
        """
        self.uri = uri
        self.websocket = None

    async def get_websocket(self):
        """Get or create websocket connection.

        Returns:
            Active websocket connection
        """
        if self.websocket is None:
            self.websocket = await websockets.connect(self.uri)
        return self.websocket

    async def stream_messages(self):
        """Async generator yielding messages continuously from firehose.

        Yields:
            Parsed JSON message dictionaries
        """
        ws = await self.get_websocket()
        while True:
            try:
                message = await ws.recv()
                yield json.loads(message)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                print(f"Connection error: {e}")
                self.websocket = None
                ws = await self.get_websocket()

    async def get_one_message(self) -> Optional[dict]:
        """Return a single message from firehose.

        Returns:
            Parsed JSON message dictionary
        """
        async for msg in self.stream_messages():
            return msg

    async def stream_matching_messages(self, keywords: set):
        """Stream only messages with posts matching keywords.

        Args:
            keywords: Set of keywords to filter on

        Yields:
            Modified messages with 'matching_keyword_set', 'post_url', and 'post_type' fields added
        """
        async for msg in self.stream_messages():
            # Extract post text from message
            post_text = self._extract_post_text(msg)
            matching_kws = self.keyword_match(keywords, post_text)

            # Only yield if keywords matched
            if matching_kws:
                msg["matching_keyword_set"] = list(matching_kws)
                msg = self._add_post_url_to_message(msg)
                msg["post_type"] = self.get_post_type(msg)
                yield msg

    def keyword_match(self, kws: set, post_text: str) -> Optional[set]:
        """Return a set of keywords that match as whole words in post_text.

        Uses regex with flexible word boundaries to match whole words only.
        Handles special characters gracefully. For example:
        - 'ice' will NOT match in 'nice' but WILL match in 'ice cream'
        - 'c++' will match in 'I code in c++'
        - 'c#' will match in 'I code in c#'

        Args:
            kws: Set of keywords to search for
            post_text: The post text to search in

        Returns:
            Set of matching keywords, or None if no matches found
        """
        if not kws or not post_text:
            return None

        matching = set()
        text_lower = post_text.lower()

        for keyword in kws:
            keyword_lower = keyword.lower()
            # Use lookahead/lookbehind with non-word characters or boundaries
            # This allows matching keywords with special characters like c++ or c#
            pattern = r"(?:^|\W)" + re.escape(keyword_lower) + r"(?:\W|$)"
            if re.search(pattern, text_lower):
                matching.add(keyword)

        return matching if matching else None

    def _extract_post_text(self, message: dict) -> str:
        """Extract post text from a Bluesky message.

        Args:
            message: Raw message from Jetstream

        Returns:
            Post text if found, empty string otherwise
        """
        try:
            return message.get("commit", {}).get("record", {}).get("text", "")
        except (KeyError, TypeError):
            return ""

    def get_post_type(self, message: dict) -> str:
        """Determine if a post is a standalone post, reply, or comment.

        Logic:
        - No 'reply' field → 'post' (standalone)
        - Has 'reply' + parent == root → 'reply' (direct reply to original)
        - Has 'reply' + parent != root → 'comment' (reply to someone's reply)

        Args:
            message: Raw message from Jetstream

        Returns:
            One of: 'post', 'reply', 'comment', or 'unknown'
        """
        try:
            record = message.get("commit", {}).get("record", {})
            reply = record.get("reply")

            if not reply:
                return "post"

            # Check if parent == root (direct reply) or parent != root (comment in thread)
            parent_uri = reply.get("parent", {}).get("uri")
            root_uri = reply.get("root", {}).get("uri")

            if parent_uri == root_uri:
                return "reply"  # Direct reply to original post
            return "comment"  # Reply to a comment in thread
        except (KeyError, TypeError, AttributeError):
            return "unknown"

    def _parse_at_uri(self, at_uri: str) -> Optional[str]:
        """Extract the record key (rkey) from an AT URI.

        AT URI format: at://did:plc:xxx/app.bsky.feed.post/rkey

        Args:
            at_uri: The AT protocol URI string

        Returns:
            The record key if successfully parsed, None otherwise
        """
        if not at_uri or not isinstance(at_uri, str):
            return None

        try:
            # Split by '/' and get the last component (rkey)
            parts = at_uri.strip().split("/")
            if len(parts) >= 1:
                return parts[-1]
        except (IndexError, AttributeError):
            pass

        return None

    def compose_post_url(self, did: str, rkey: str) -> str:
        """Compose a Bluesky web URL for a post.

        Args:
            did: The user's DID (Decentralized Identifier)
            rkey: The record key of the post

        Returns:
            A Bluesky web URL pointing to the post
        """
        return f"https://bsky.app/profile/{did}/post/{rkey}"

    def _add_post_url_to_message(self, message: dict) -> dict:
        """Add a Bluesky post URL to a message.

        Extracts the DID and rkey from the message and composes the URL.
        Constructs the AT URI if not present.

        Args:
            message: The Jetstream message dict

        Returns:
            Modified message with 'post_url' field added
        """
        try:
            did = message.get("did")
            rkey = message.get("commit", {}).get("rkey")

            if did and rkey:
                message["post_url"] = self.compose_post_url(did, rkey)
        except (KeyError, TypeError, AttributeError):
            pass

        return message

    async def close(self):
        """Close the websocket connection."""
        if self.websocket:
            await self.websocket.close()

def get_db_connection() -> psycopg2.extensions.connection:
    """Get a PostgreSQL database connection hosted in AWS RDS.

    Reads connection parameters from environment variables:
        - DB_HOST: RDS endpoint
        - DB_PORT: Database port (default: 5432)
        - DB_NAME: Database name
        - DB_USER: Database user
        - DB_PASSWORD: Database password

    Returns:
        psycopg2 connection object

    Raises:
        psycopg2.OperationalError: If connection fails
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Failed to connect to database: {e}")
        raise


def get_keywords_from_db(cursor) -> set:
    """Fetch all keywords from the database and return as a set.

    Args:
        cursor: A psycopg2 database cursor

    Returns:
        Set of keyword strings, or None if query fails or no keywords found

    Raises:
        psycopg2.DatabaseError: If query execution fails
    """
    try:
        cursor.execute("SELECT keyword_name FROM keywords;")
        results = cursor.fetchall()

        if not results:
            return None

        # Extract keyword_name from each row tuple
        keywords = {row[0] for row in results}
        return keywords
    except psycopg2.DatabaseError as e:
        print(f"Database query failed: {e}")
        raise


if __name__ == "__main__":
    trending_keywords = {"ice", "maga", "trump", "putin", "meme"}

    async def main():
        """Extract one matching message and save to JSON."""
        firehose = BlueskyFirehose()
        try:
            async for msg in firehose.stream_matching_messages(trending_keywords):
                # Message already has matching_keyword_set added by stream_matching_messages
                with open("one_message.json", "w", encoding="utf-8") as f:
                    json.dump(msg, f, indent=2)
                print("Message saved to one_message.json")
                break  # Only get one matching message
        finally:
            await firehose.close()

    asyncio.run(main())

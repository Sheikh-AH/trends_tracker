"""
This code is meant to extract and filter out the posts that match a set of
keywords.

Utilites:
    >Get DB connection
    >Query keywords list
    >Extract each post dict from jetstream firehose
    >Check if post matches any of the keywords
"""




import asyncio
import websockets
import json
import os
import psycopg2


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
            except Exception as e:
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

    async def close(self):
        """Close the websocket connection."""
        if self.websocket:
            await self.websocket.close()

def keyword_match(keywords: set, post_text: str) -> Optional[set]:
    """Return a set of matching keywords in post_text"""

    matching = set()
    # Current approach (linear) - O(k*n) average case
    text_lower = post_text.lower()  # O(n) - done once
    for keyword in keywords:
        if keyword.lower() in text_lower:  # O(n) per keyword, but efficient with Python's string search
            matching.add(keyword)

    if len(matching) == 0:
        return None

    return matching


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
            port=os.getenv("DB_PORT", 5432),
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
    keywords = {"ice", "maga", "trump", "putin", "meme"}

    async def main():
        firehose = BlueskyFirehose()
        msg = await firehose.get_one_message()
        await firehose.close()
        if msg is not None:
            with open("one_message.json", "w") as f:
                json.dump(msg, f, indent=2)
            print("Message saved to one_message.json")
        else:
            print("No message to save.")

    asyncio.run(main())

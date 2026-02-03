"""Load BlueSky data into PostgreSQL database."""

from dotenv import load_dotenv
from os import environ as ENV, _Environ
import psycopg2


def get_db_connection(config: _Environ):
    """Establish a database connection using environment variables."""
    conn = psycopg2.connect(
        dbname=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD"),
        host=config.get("DB_HOST"),
        port=config.get("DB_PORT", 5432)
    )
    return conn


def upload_batch(posts, connection):
    """Batch load 100 posts into the database."""
    if not posts:
        return

    cursor = connection.cursor()

    # Insert into bluesky_posts
    cursor.executemany(
        """INSERT INTO bluesky_posts 
           (post_uri, posted_at, author_did, text, sentiment_score, ingested_at, reply_uri, repost_uri)
           VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
           ON CONFLICT (post_uri) DO NOTHING""",
        [(
            p["post_uri"],
            p["posted_at"],
            p["author_did"],
            p["text"],
            p["sentiment"],
            p.get("reply_uri"),
            p.get("repost_uri"),
        ) for p in posts]
    )

    # Insert into matches (one row per keyword per post)
    match_rows = []
    for p in posts:
        for keyword in p["keywords"]:
            match_rows.append((p["post_uri"], keyword))

    if match_rows:
        cursor.executemany(
            """INSERT INTO matches (post_uri, keyword_value)
               VALUES (%s, %s)
               ON CONFLICT DO NOTHING""",
            match_rows
        )

    connection.commit()


if __name__ == "__main__":
    load_dotenv()
    conn = get_db_connection(ENV)
    posts = []  # Replace with actual posts to load

    buffer = []
    BATCH_SIZE = 500

    for post in posts:
        buffer.append(post)

        if len(buffer) >= BATCH_SIZE:
            upload_batch(buffer, conn)
            buffer = []

    # Flush remaining
    if buffer:
        upload_batch(buffer, conn)
    pass

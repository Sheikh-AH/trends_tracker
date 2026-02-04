"""Load BlueSky data into PostgreSQL database."""

import logging
from os import environ as ENV, _Environ
from dotenv import load_dotenv
import psycopg2

logger = logging.getLogger(__name__)


def get_db_connection(config: _Environ):
    """Establish a database connection using environment variables."""
    conn = psycopg2.connect(
        dbname=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD"),
        host=config.get("DB_HOST"),
        port=config.get("DB_PORT", 5432)
    )
    logger.info("Database connection established.")
    return conn


def upload_batch(posts, connection):
    """Batch load 100 posts into the database."""
    if not posts:
        return

    cursor = connection.cursor()
    logger.info(f"Uploading batch of {len(posts)} posts to database.")

    # Insert into bluesky_posts
    cursor.executemany(
        """INSERT INTO bluesky_posts 
           (post_uri, posted_at, author_did, text, sentiment_score, ingested_at, reply_uri, repost_uri)
           VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
           ON CONFLICT (post_uri) DO NOTHING""",
        [(
            p["post_uri"],
            p["commit"]["record"]["createdAt"],
            p["did"],
            p["commit"]["record"]["text"],
            p["sentiment"],
            p.get("commit", {}).get("record", {}).get(
                "reply", {}).get("parent", {}).get("uri"),
            p.get("repost_uri"),
        ) for p in posts]
    )

    logger.info("Inserted posts into bluesky_posts table.")

    # Insert into matches (one row per keyword per post)
    match_rows = []
    for p in posts:
        for keyword in p["matching_keywords"]:
            match_rows.append((p["post_uri"], keyword))

    if match_rows:
        cursor.executemany(
            """INSERT INTO matches (post_uri, keyword_value)
               VALUES (%s, %s)
               ON CONFLICT DO NOTHING""",
            match_rows
        )

        logger.info("Inserted matching keywords into matches table.")

    connection.commit()


def load_data(conn, posts, batch_size: int = 500):
    """Load posts into the database in batches."""

    logger.info("Starting data load into database...")
    buffer = []

    for post in posts:
        buffer.append(post)
        if len(buffer) >= batch_size:
            upload_batch(buffer, conn)
            buffer = []

    logger.info("Data load complete.")
    # Flush remaining
    if buffer:
        upload_batch(buffer, conn)

    conn.close()


if __name__ == "__main__":
    pass

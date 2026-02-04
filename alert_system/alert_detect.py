"""This module detects spikes in keyword mentions over the last 5 minutes compared to the average over the last 24 hours."""
import os
import psycopg2
from datetime import datetime, timezone, timedelta


def get_db_connection() -> psycopg2.extensions.connection:
    """Establishes and returns a database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def get_all_keywords() -> list[str]:
    """Fetches all distinct keywords from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT keyword_value FROM keywords")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [row[0] for row in rows]


def get_post_count_last_5_min(keyword: str) -> int:
    """Fetches the count of posts mentioning the keyword in the last 5 minutes."""
    conn = get_db_connection()
    cur = conn.cursor()

    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

    cur.execute("""
        SELECT COUNT(*) FROM matches
        WHERE keyword_value = %s
        AND match_id IN (
            SELECT m.match_id FROM matches m
            JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
            WHERE bp.posted_at >= %s
        )
    """, (keyword, five_min_ago))

    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    return count


def get_average_5_min_count_last_24h(keyword: str) -> float:
    """Calculates the average count of posts mentioning the keyword in 5-minute intervals over the last 24 hours."""
    conn = get_db_connection()
    cur = conn.cursor()

    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)

    cur.execute("""
        SELECT COUNT(*) FROM matches
        WHERE keyword_value = %s
        AND match_id IN (
            SELECT m.match_id FROM matches m
            JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
            WHERE bp.posted_at >= %s
        )
    """, (keyword, twenty_four_hours_ago))

    total_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    # 24 hours = 288 five-minute periods
    average = total_count / 288 if total_count > 0 else 0

    return average


def detect_spikes() -> list[dict]:
    """Detects keywords with spikes in mentions over the last 5 minutes compared to the average over the last 24 hours."""
    keywords = get_all_keywords()
    spiking_keywords = []

    print(f"Checking {len(keywords)} keywords for spikes...")

    for keyword in keywords:
        current_count = get_post_count_last_5_min(keyword)
        average_count = get_average_5_min_count_last_24h(keyword)

        # Spike if current count is 3x the average (and at least 50 posts)
        if current_count >= 50 and average_count > 0 and current_count >= (average_count * 3):
            print(
                f"SPIKE: {keyword} - {current_count} posts (avg: {average_count:.1f})")
            spiking_keywords.append({
                "keyword": keyword,
                "current_count": current_count,
                "average_count": average_count
            })

    print(f"Found {len(spiking_keywords)} spiking keywords")
    return spiking_keywords


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    spikes = detect_spikes()
    print(spikes)

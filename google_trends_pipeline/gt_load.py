import psycopg2
import os
from dotenv import load_dotenv


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def load(data: list):
    if not data:
        print("No data to load")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    insert_query = """
        INSERT INTO google_trends (keyword_value, search_volume, trend_date)
        VALUES (%s, %s, %s)
    """

    for item in data:
        cur.execute(insert_query, (
            item["keyword_value"],
            item["search_volume"],
            item["trend_date"]
        ))

    conn.commit()
    print(f"Loaded {len(data)} records into google_trends")

    cur.close()
    conn.close()


if __name__ == "__main__":
    from datetime import datetime, timezone

    load_dotenv()

    sample = [{
        "keyword_value": "matcha",
        "search_volume": 75,
        "trend_date": datetime.now(timezone.utc)
    }]
    load(sample)

import psycopg2
from pytrends.request import TrendReq
import time
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


def get_keywords_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT keyword_value FROM keywords")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    keywords = {row[0] for row in rows}
    return keywords


def get_search_volume(keywords: set):
    if not keywords:
        print("No keywords found in database")
        return []

    pytrends = TrendReq(hl='en-GB', tz=0)
    results = []
    keyword_list = list(keywords)

    for i in range(0, len(keyword_list), 5):
        batch = keyword_list[i:i+5]

        try:
            pytrends.build_payload(batch, cat=0, timeframe='now 7-d', geo='GB')
            data = pytrends.interest_over_time()

            if not data.empty:
                for keyword in batch:
                    if keyword in data.columns:
                        avg_volume = int(data[keyword].mean())
                        results.append({
                            "keyword_value": keyword,
                            "search_volume": avg_volume
                        })

            time.sleep(2)

        except Exception as e:
            print(f"Error fetching batch {batch}: {e}")
            continue

    return results


def extract():
    print("Extracting keywords from database...")
    keywords = get_keywords_from_db()
    print(f"Found {len(keywords)} keywords: {keywords}")

    print("Fetching search volumes from Google Trends...")
    raw_data = get_search_volume(keywords)
    print(f"Got data for {len(raw_data)} keywords")

    return raw_data


if __name__ == "__main__":
    load_dotenv()
    data = extract()
    print(data)

"""
Lambda function to generate daily summaries for users using GPT-5-nano via OpenRouter.

This function:
1. Fetches all users from the database
2. For each user, retrieves their tracked keywords via user_keywords
3. Fetches recent Bluesky posts (via matches) and Google Trends data for those keywords
4. Uses GPT-5-nano to generate a personalized summary
5. Upserts the summary into the llm_summary table

Environment variables required:
- DB_HOST: RDS endpoint
- DB_NAME: Database name
- DB_USER: Database username
- DB_PASSWORD: Database password
- OPENROUTER_API_KEY: OpenRouter API key
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from requests import post, exceptions

# Configure logging - console only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# OpenRouter configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_db_connection():
    """Create and return a database connection."""
    logger.info("Attempting to establish database connection...")
    try:
        conn = connect(
            host=os.environ.get("DB_HOST"),
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            port=os.environ.get("DB_PORT", 5432)
        )
        logger.info(
            f"Successfully connected to database: {os.environ.get('DB_NAME')}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def fetch_all_users(conn) -> list[dict]:
    """Fetch all users from the database."""
    logger.info("Fetching all users from database...")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT user_id, email
                FROM users
            """)
            users = cur.fetchall()
        logger.info(f"Successfully fetched {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise


def fetch_user_keywords(conn, user_id: int) -> list[dict]:
    """Fetch all keywords a user is tracking via the user_keywords junction table."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT k.keyword_id, k.keyword_value
            FROM keywords k
            INNER JOIN user_keywords uk ON k.keyword_id = uk.keyword_id
            WHERE uk.user_id = %s
        """, (user_id,))
        return cur.fetchall()


def fetch_bluesky_posts_for_user_keywords(
    conn, keyword_values: list[str]
) -> list[dict]:
    """Fetch Bluesky posts matching any of the user's keywords from the previous day."""
    if not keyword_values:
        return []

    # Calculate previous day boundaries
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today - timedelta(days=1)
    yesterday_end = today

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                bp.text,
                bp.sentiment_score,
                bp.posted_at,
                m.keyword_value
            FROM bluesky_posts bp
            INNER JOIN matches m ON bp.post_uri = m.post_uri
            WHERE m.keyword_value = ANY(%s)
              AND bp.posted_at >= %s
              AND bp.posted_at < %s
            ORDER BY bp.posted_at DESC
            LIMIT 500;
        """, (keyword_values, yesterday_start, yesterday_end))
        return cur.fetchall()


def fetch_google_trends_for_user_keywords(
    conn, keyword_values: list[str]
) -> list[dict]:
    """Fetch Google Trends data for the user's keywords from the previous day."""
    if not keyword_values:
        return []

    # Calculate previous day boundaries
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today - timedelta(days=1)
    yesterday_end = today

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                keyword_value,
                search_volume,
                trend_date
            FROM google_trends
            WHERE keyword_value = ANY(%s)
              AND trend_date >= %s
              AND trend_date < %s
            ORDER BY trend_date DESC
        """, (keyword_values, yesterday_start, yesterday_end))
        return cur.fetchall()


def build_prompt(keywords: list[str], posts: list[dict], trends: list[dict]) -> str:
    """Build the prompt for the LLM to generate a user's summary."""

    keywords_list = ", ".join(keywords)

    # Group posts by keyword
    posts_by_keyword = {}
    for post in posts:
        kw = post['keyword_value']
        if kw not in posts_by_keyword:
            posts_by_keyword[kw] = []
        posts_by_keyword[kw].append(post)

    # Format Bluesky posts section
    if posts:
        posts_sections = []
        for kw, posts in posts_by_keyword.items():
            posts_text = "\n".join([
                f"  - {post['text']}"
                for post in posts
            ])
            posts_sections.append(
                f"Keyword '{kw}' ({len(posts)} posts):\n{posts_text}")

        posts_section = f"""
BLUESKY POSTS (last 24 hours):
Total posts across all keywords: {len(posts)}

{chr(10).join(posts_sections)}
"""
    else:
        posts_section = "\nBLUESKY POSTS: No posts found in the last 24 hours.\n"

    # Group trends by keyword
    trends_by_keyword = {}
    for trend in trends:
        kw = trend['keyword_value']
        if kw not in trends_by_keyword:
            trends_by_keyword[kw] = []
        trends_by_keyword[kw].append(trend)

    # Format Google Trends section
    if trends:
        trends_sections = []
        for kw, trends in trends_by_keyword.items():
            trends_text = ", ".join([
                f"{t['trend_date'].strftime('%m/%d')}: {t['search_volume']}"
                for t in trends[:7]
            ])
            trends_sections.append(f"  {kw}: {trends_text}")

        trends_section = f"""
GOOGLE TRENDS (last 7 days):
{chr(10).join(trends_sections)}
"""
    else:
        trends_section = "\nGOOGLE TRENDS: No data available.\n"

    # Calculate sentiment breakdown across all posts
    sentiment_section = ""
    if posts:
        sentiment_scores = [p['sentiment_score']
                            for p in posts if p.get('sentiment_score')]
        if sentiment_scores:
            avg_sentiment = sum(float(s)
                                for s in sentiment_scores) / len(sentiment_scores)
            sentiment_section = f"\nOVERALL SENTIMENT SCORE: {avg_sentiment:.2f} (scale: -1 negative to +1 positive)\n"

    prompt = f"""Analyze the following data for a user tracking these keywords: {keywords_list}

{posts_section}
{sentiment_section}
{trends_section}

Please provide a personalized daily summary that includes:
1. Overview of activity across all tracked keywords (which are hot, which are quiet)
2. Key themes or discussions happening for each active keyword
3. Overall sentiment trends and any notable shifts
4. Which keywords are rising/falling in interest
5. Any notable posts or emerging narratives worth attention

Keep the summary concise (2-3 paragraphs) and actionable for someone monitoring these topics for brand/reputation purposes."""

    return prompt


def generate_summary_with_openrouter(prompt: str) -> Optional[str]:
    """Call OpenRouter API to generate a summary using GPT-5-nano."""
    logger.info("Calling OpenRouter API to generate summary...")

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not set!")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://trendgetter.app",
            "X-Title": "Trend Getter"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        # Log response status and body for debugging
        logger.info(f"OpenRouter API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"OpenRouter API error response: {response.text}")

        response.raise_for_status()

        result = response.json()
        summary = result["choices"][0]["message"]["content"]
        logger.info("Successfully generated summary from OpenRouter API")
        return summary

    except exceptions.RequestException as e:
        logger.error(f"OpenRouter API request error: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from OpenRouter: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter: {e}")
        return None


def upsert_summary(conn, user_id: int, summary: str) -> None:
    """Insert a new summary for a user (adds to existing summaries instead of replacing)."""
    with conn.cursor() as cur:
        # Insert new summary
        cur.execute("""
            INSERT INTO llm_summary (user_id, summary)
            VALUES (%s, %s)
        """, (user_id, summary))
    conn.commit()


def process_user(conn, user_id: int, email: str) -> bool:
    """Process a single user: fetch their keywords, get data, generate summary, save."""
    logger.info(f"Processing user: {user_id} ({email})")

    # Fetch user's keywords
    keywords = fetch_user_keywords(conn, user_id)
    if not keywords:
        logger.info(f"User {user_id} has no tracked keywords, skipping")
        return True  # Not a failure, just nothing to do

    keyword_values = [kw['keyword_value'] for kw in keywords]
    logger.info(
        f"User {user_id} is tracking {len(keyword_values)} keywords: {keyword_values}")

    # Fetch data for all user's keywords
    bluesky_posts = fetch_bluesky_posts_for_user_keywords(conn, keyword_values)
    google_trends = fetch_google_trends_for_user_keywords(conn, keyword_values)

    logger.info(
        f"Fetched {len(bluesky_posts)} posts and "
        f"{len(google_trends)} trend data points for user {user_id}"
    )

    # Build prompt and generate summary
    prompt = build_prompt(keyword_values, bluesky_posts, google_trends)
    summary = generate_summary_with_openrouter(prompt)

    if summary:
        upsert_summary(conn, user_id, summary)
        logger.info(f"Successfully saved summary for user {user_id}")
        return True
    else:
        logger.warning(f"Failed to generate summary for user {user_id}")
        return False


def lambda_handler(event, context):
    """Main Lambda handler function."""
    logger.info("Starting LLM summary generation")

    results = {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "users": []
    }

    try:
        conn = get_db_connection()
        users = fetch_all_users(conn)
        logger.info(f"Found {len(users)} users to process")

    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Database connection failed",
                "message": str(e)
            })
        }

    for user in users:
        user_id = user['user_id']
        email = user['email']
        results["processed"] += 1

        try:
            # Check if user has keywords
            keywords = fetch_user_keywords(conn, user_id)
            if not keywords:
                results["skipped"] += 1
                results["users"].append({
                    "user_id": user_id,
                    "status": "skipped",
                    "reason": "no keywords"
                })
                continue

            success = process_user(conn, user_id, email)

            if success:
                results["succeeded"] += 1
                results["users"].append({
                    "user_id": user_id,
                    "status": "success",
                    "keywords_count": len(keywords)
                })
            else:
                results["failed"] += 1
                results["users"].append({
                    "user_id": user_id,
                    "status": "failed"
                })

        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            results["failed"] += 1
            results["users"].append({
                "user_id": user_id,
                "status": "error",
                "error": str(e)
            })

    conn.close()

    logger.info(
        f"Completed: {results['succeeded']} succeeded, "
        f"{results['skipped']} skipped, {results['failed']} failed"
    )

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(json.dumps(json.loads(result["body"]), indent=2))

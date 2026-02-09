"""This module handles sending email alerts to users when spikes in keyword mentions are detected."""
import os
import urllib.parse
import psycopg2
import boto3
from datetime import datetime, timezone, timedelta


# In-memory dict to track alerts sent today
# Format: { "user_id:keyword": True }
alerts_sent_today = {}


def get_db_connection() -> psycopg2.extensions.connection:
    """Establishes and returns a database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def get_users_for_keyword(keyword: str) -> list[dict]:
    """Fetches users who are subscribed to the keyword and have email alerts enabled."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.user_id, u.email
        FROM users u
        JOIN user_keywords uk ON u.user_id = uk.user_id
        JOIN keywords k ON uk.keyword_id = k.keyword_id
        WHERE k.keyword_value = %s
        AND u.send_alert = true
        AND u.send_email = true
    """, (keyword,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{"user_id": row[0], "email": row[1]} for row in rows]


def get_recent_posts_for_keyword(keyword: str, limit: int = 3) -> list[dict]:
    """Fetches the most recent posts mentioning the keyword."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT bp.text, bp.author_did, bp.posted_at, bp.post_uri
        FROM bluesky_posts bp
        JOIN matches m ON bp.post_uri = m.post_uri
        WHERE m.keyword_value = %s
        ORDER BY bp.posted_at DESC
        LIMIT %s
    """, (keyword, limit))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "text": row[0],
            "author_did": row[1],
            "posted_at": row[2],
            "post_uri": row[3]
        }
        for row in rows
    ]


def already_alerted_today(user_id: int, keyword: str) -> bool:
    """Checks if an alert has already been sent today for the user and keyword."""
    key = f"{user_id}:{keyword}"
    return alerts_sent_today.get(key, False)


def mark_as_alerted(user_id: int, keyword: str) -> None:
    """Marks that an alert has been sent today for the user and keyword."""
    key = f"{user_id}:{keyword}"
    alerts_sent_today[key] = True


def format_post_time(posted_at: datetime) -> str:
    """Formats a post timestamp into a human-readable string."""
    if posted_at is None:
        return "Recently"
    now = datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    diff = now - posted_at
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} min ago"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        return posted_at.strftime("%b %d, %Y")


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncates text to a maximum length, adding ellipsis if needed."""
    if text and len(text) > max_length:
        return text[:max_length].rsplit(' ', 1)[0] + "..."
    return text or ""


def load_email_template() -> str:
    """Loads the HTML email template from file."""
    template_path = os.path.join(os.path.dirname(__file__), "alert_email.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def build_html_email(keyword: str, current_count: int, posts: list[dict], logo_url: str = None) -> str:
    """Builds a styled HTML email body using the template."""
    search_url = f"https://bsky.app/search?q={urllib.parse.quote(keyword)}"

    posts_html = ""
    if posts:
        for post in posts:
            post_text = truncate_text(post.get("text", ""))
            time_ago = format_post_time(post.get("posted_at"))
            author = post.get("author_did", "user")
            if author and author.startswith("did:"):
                author = "Bluesky User"

            posts_html += f"""
            <div style="background-color: #f8fafc; padding: 16px; margin-bottom: 12px; border-left: 4px solid #1976D2;">
                <p style="margin: 0 0 8px 0; color: #334155; font-size: 14px; line-height: 1.6;">{post_text}</p>
                <p style="margin: 0; color: #64748b; font-size: 12px;">{author} · {time_ago}</p>
            </div>
            """
    else:
        posts_html = '<p style="color: #64748b; font-style: italic;">No recent posts available</p>'

    # Build logo section (same pattern as weekly report)
    if logo_url:
        logo_section = f'<img src="{logo_url}" alt="TrendFunnel" style="height: 40px; width: auto;"><span style="font-size: 20px; font-weight: 700; color: #0D47A1; margin-left: 12px; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif; vertical-align: middle;">TrendFunnel</span>'
    else:
        logo_section = '<span style="font-size: 20px; font-weight: 700; color: #0D47A1; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif;">TrendFunnel</span>'

    template = load_email_template()

    html = template.replace("{{logo_section}}", logo_section)
    html = html.replace("{{keyword}}", keyword)
    html = html.replace("{{current_count}}", str(current_count))
    html = html.replace("{{posts_html}}", posts_html)
    html = html.replace("{{search_url}}", search_url)

    return html


def send_email(to_email: str, keyword: str, current_count: int) -> bool:
    """Sends an email alert via AWS SES."""
    ses = boto3.client('ses', region_name=os.getenv("AWS_REGION"))

    subject = f" Spike Alert: #{keyword} is trending!"

    # Get recent posts for the email
    posts = get_recent_posts_for_keyword(keyword, limit=3)

    # Build HTML email
    logo_url = "https://c21-trends-funnel-assets.s3.eu-west-2.amazonaws.com/logo_blue.png"
    html_body = build_html_email(
        keyword, current_count, posts, logo_url=logo_url)

    try:
        ses.send_email(
            Source=os.getenv("SENDER_EMAIL"),
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": html_body}
                }
            }
        )
        print(f"Email sent to {to_email} for keyword '{keyword}'")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False


def send_alerts(spiking_keywords: list[dict]) -> None:
    """Sends email alerts for detected keyword spikes."""
    if not spiking_keywords:
        print("No spikes to alert on")
        return

    total_sent = 0

    for spike in spiking_keywords:
        keyword = spike["keyword"]
        current_count = spike["current_count"]

        users = get_users_for_keyword(keyword)
        print(f"Found {len(users)} users subscribed to '{keyword}'")

        for user in users:
            user_id = user["user_id"]
            email = user["email"]

            if already_alerted_today(user_id, keyword):
                print(
                    f"Skipping {email} - already alerted today for '{keyword}'")
                continue

            if send_email(email, keyword, current_count):
                mark_as_alerted(user_id, keyword)
                total_sent += 1

    print(f"Total alerts sent: {total_sent}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_spikes = [{"keyword": "matcha",
                    "current_count": 15, "average_count": 5}]
    send_alerts(test_spikes)

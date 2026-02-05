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


def build_html_email(keyword: str, current_count: int, posts: list[dict]) -> str:
    """Builds a styled HTML email body."""
    search_url = f"https://bsky.app/search?q={urllib.parse.quote(keyword)}"

    posts_html = ""
    for post in posts:
        post_text = truncate_text(post.get("text", ""))
        time_ago = format_post_time(post.get("posted_at"))
        # Extract handle from author_did or use a placeholder
        author = post.get("author_did", "user")
        if author and author.startswith("did:"):
            author = "Bluesky User"

        posts_html += f"""
        <div style="background-color: #f8f9fa; border-radius: 12px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #0085ff;">
            <p style="margin: 0 0 8px 0; color: #333; font-size: 14px; line-height: 1.5;">{post_text}</p>
            <p style="margin: 0; color: #666; font-size: 12px;">🦋 {author} · {time_ago}</p>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f0f2f5;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f0f2f5;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0085ff 0%, #00c6ff 100%); padding: 32px; text-align: center; border-radius: 16px 16px 0 0;">
                                <div style="font-size: 48px; margin-bottom: 8px;">📈</div>
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Spike Alert!</h1>
                            </td>
                        </tr>
                        
                        <!-- Main Content -->
                        <tr>
                            <td style="padding: 32px;">
                                <!-- Keyword Badge -->
                                <div style="text-align: center; margin-bottom: 24px;">
                                    <span style="display: inline-block; background-color: #e8f4ff; color: #0085ff; padding: 8px 20px; border-radius: 20px; font-size: 18px; font-weight: 600;">
                                        #{keyword}
                                    </span>
                                </div>
                                
                                <!-- Stats Box -->
                                <div style="background-color: #fff8e6; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                                    <div style="font-size: 36px; font-weight: 700; color: #f59e0b;">{current_count}</div>
                                    <div style="color: #666; font-size: 14px;">posts in the last 5 minutes</div>
                                </div>
                                
                                <p style="color: #333; font-size: 15px; line-height: 1.6; text-align: center; margin-bottom: 24px;">
                                    Your keyword <strong>"{keyword}"</strong> is trending on Bluesky right now! Here are some recent posts:
                                </p>
                                
                                <!-- Recent Posts -->
                                <div style="margin-bottom: 24px;">
                                    {posts_html if posts_html else '<p style="color: #666; text-align: center; font-style: italic;">No recent posts available</p>'}
                                </div>
                                
                                <!-- CTA Button -->
                                <div style="text-align: center;">
                                    <a href="{search_url}" style="display: inline-block; background: linear-gradient(135deg, #0085ff 0%, #00c6ff 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 25px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 12px rgba(0, 133, 255, 0.4);">
                                        🔍 See all posts on Bluesky
                                    </a>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; text-align: center; border-top: 1px solid #eee;">
                                <p style="margin: 0; color: #999; font-size: 12px;">
                                    You're receiving this because you enabled spike alerts for this keyword.<br>
                                    Manage your preferences in your dashboard.
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def send_email(to_email: str, keyword: str, current_count: int) -> bool:
    """Sends an email alert via AWS SES."""
    ses = boto3.client('ses', region_name=os.getenv("AWS_REGION"))

    subject = f"📈 Spike Alert: #{keyword} is trending!"

    # Get recent posts for the email
    posts = get_recent_posts_for_keyword(keyword, limit=3)

    # Build HTML email
    html_body = build_html_email(keyword, current_count, posts)

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

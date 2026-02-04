"""This module handles sending email alerts to users when spikes in keyword mentions are detected."""
import os
import psycopg2
import boto3


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


def already_alerted_today(user_id: int, keyword: str) -> bool:
    """Checks if an alert has already been sent today for the user and keyword."""
    key = f"{user_id}:{keyword}"
    return alerts_sent_today.get(key, False)


def mark_as_alerted(user_id: int, keyword: str) -> None:
    """Marks that an alert has been sent today for the user and keyword."""
    key = f"{user_id}:{keyword}"
    alerts_sent_today[key] = True


def send_email(to_email: str, keyword: str, current_count: int) -> bool:
    """Sends an email alert via AWS SES."""
    ses = boto3.client('ses', region_name=os.getenv("AWS_REGION"))

    subject = f"🔔 Spike Alert: {keyword}"
    body = f"Heads up! Your keyword '{keyword}' is being mentioned a lot on BlueSky right now. We've seen {current_count} posts in the last 5 minutes, which is higher than usual."

    try:
        ses.send_email(
            Source=os.getenv("SENDER_EMAIL"),
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}}
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

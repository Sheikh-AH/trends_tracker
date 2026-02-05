"""Main pipeline for generating and sending weekly email reports."""
import os
import boto3
from report_data import get_all_users, get_user_report_data
from gen_html_report import build_weekly_report_email


def send_email(to_email: str, html_body: str) -> bool:
    """Sends the weekly report email via AWS SES."""
    ses = boto3.client('ses', region_name=os.getenv("AWS_REGION"))

    subject = "Your Weekly Trends Report"

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
        print(f"Weekly report sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send report to {to_email}: {e}")
        return False


def run_weekly_report_pipeline() -> dict:
    """Runs the full weekly report pipeline for all users."""
    print("Starting weekly report pipeline...")

    users = get_all_users()
    print(f"Found {len(users)} users with email enabled")

    total_sent = 0
    total_failed = 0

    for user in users:
        user_id = user["user_id"]
        email = user["email"]

        print(f"Generating report for user {user_id} ({email})...")

        try:
            # Get all report data for this user
            report_data = get_user_report_data(user_id)

            # Skip if user has no keywords
            if not report_data["keywords"]:
                print(f"Skipping {email} - no keywords tracked")
                continue

            # Build the HTML email
            html_body = build_weekly_report_email(report_data, email)

            # Send the email
            if send_email(email, html_body):
                total_sent += 1
            else:
                total_failed += 1

        except Exception as e:
            print(f"Error processing user {user_id}: {e}")
            total_failed += 1

    print(
        f"Weekly report pipeline complete: {total_sent} sent, {total_failed} failed")

    return {
        "total_users": len(users),
        "total_sent": total_sent,
        "total_failed": total_failed
    }


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    result = run_weekly_report_pipeline()

    return {
        "statusCode": 200,
        "body": result
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_weekly_report_pipeline()

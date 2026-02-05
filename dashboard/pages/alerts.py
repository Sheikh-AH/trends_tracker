"""Email alerts and notifications management dashboard."""

import os
import streamlit as st
import boto3
from dotenv import load_dotenv
from psycopg2 import connect

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )


ses_client = boto3.client(
    'ses',
    region_name=os.getenv('AWS_REGION', 'eu-west-2'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)

def is_email_verified(email: str) -> bool:
    """Check if the email is verified with AWS SES."""
    response = ses_client.list_verified_email_addresses()
    return email in response['VerifiedEmailAddresses']

def send_verification_email(email: str) -> dict:
    """Send a verification email to the specified address."""
    return ses_client.verify_email_identity(EmailAddress=email)

def verify_email(email: str) -> bool:
    """Verify the email address and send verification if not already verified."""
    if is_email_verified(email):
        st.success(f"{email} is a verified email address.")
        return True
    else:
        st.info(f"Sending verification to {email}")
        send_verification_email(email)
        return False
    
def update_db_alert_settings(conn, email_enabled: bool, alerts_enabled: bool):
    """Update the user's alert settings in the database."""
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE users
            SET send_email = %s, send_alert = %s
            WHERE email = %s
        """, (email_enabled, alerts_enabled, st.session_state.email))
        conn.commit()
    
def gen_email_toggle(conn):
    """Generate email toggle"""
    return st.toggle(
        "Enable Email Reports",
        value=st.session_state.emails_enabled,
        on_change=update_db_alert_settings(conn, st.session_state.emails_enabled, st.session_state.alerts_enabled),
        help="Receive a weekly email summary of trends and insights based on your keywords"
    )

def gen_alert_toggle(conn):
    """Generate alert toggle"""
    return st.toggle(
        "Enable Spike Alerts",
        value=st.session_state.alerts_enabled,
        on_change=update_db_alert_settings(conn, st.session_state.emails_enabled, st.session_state.alerts_enabled),
        help="Receive alerts for significant trend changes"
    )


def show_alerts_dashboard():
    """Display the alerts/notifications management dashboard."""

    st.markdown("---")
    st.markdown("### 📧 Email Weekly Reports")

    emails_enabled = gen_email_toggle()
    st.session_state.emails_enabled = emails_enabled

    alerts_enabled = gen_alert_toggle()
    st.session_state.alerts_enabled = alerts_enabled

    if st.session_state.emails_enabled or st.session_state.alerts_enabled:
        verified = verify_email(st.session_state.email)
        if not verified:
            emails_enabled = False
            st.session_state.emails_enabled = False
            alerts_enabled = False
            st.session_state.alerts_enabled = False

    st.markdown("---")

if __name__ == "__main__":
    
    load_dotenv()
    conn = get_db_connection()

    st.title("🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")
    show_alerts_dashboard()

    

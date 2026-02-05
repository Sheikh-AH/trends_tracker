"""Email alerts and notifications management dashboard."""

import os
import streamlit as st
import boto3
from dotenv import load_dotenv

load_dotenv()

# Initialize SES client
ses_client = boto3.client(
    'ses',
    region_name=os.getenv('AWS_REGION', 'eu-west-2'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)

def is_email_verified(email: str) -> bool:
    response = ses_client.list_verified_email_addresses()
    return email in response['VerifiedEmailAddresses']

def send_verification_email(email: str) -> dict:
    return ses_client.verify_email_identity(EmailAddress=email)

def verify_email(email: str) -> bool:
    if is_email_verified(email):
        st.success(f"{email} is a verified email address.")
        return True
    else:
        st.info(f"Sending verification to {email}")
        send_verification_email(email)
        return False
    
def gen_email_toggle():
    """Generate email toggle"""
    return st.toggle(
        "Enable Email Reports",
        value=st.session_state.emails_enabled,
        help="Receive a weekly email summary of trends and insights based on your keywords"
    )

def gen_alert_toggle():
    """Generate alert toggle"""
    return st.toggle(
        "Enable Spike Alerts",
        value=st.session_state.alerts_enabled,
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

    st.markdown("---")

    return emails_enabled, alerts_enabled


if __name__ == "__main__":
    st.title("🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")
    emails_enabled, alerts_enabled = show_alerts_dashboard()
    if emails_enabled or alerts_enabled:
        verify_email(st.session_state.email)

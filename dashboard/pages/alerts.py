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


def show_alerts_dashboard():
    """Display the alerts/notifications management dashboard."""

    st.markdown("---")

    st.markdown("### 📧 Email Weekly Reports")

    emails_enabled = st.toggle(
        "Enable Email Reports",
        value=st.session_state.emails_enabled,
        help="Receive a weekly email summary of trends and insights based on your keywords"
    )
    st.session_state.emails_enabled = emails_enabled

    alerts_enabled = st.toggle(
        "Enable Spike Alerts",
        value=st.session_state.alerts_enabled,
        help="Receive alerts for significant trend changes"
    )
    st.session_state.alerts_enabled = alerts_enabled

    if emails_enabled or alerts_enabled:
        verify_email(st.session_state.email)


    st.markdown("---")

    # Alert history placeholder
    # st.markdown("### 📜 Recent Alerts")
    # st.markdown(
    #     "*Alert history will be displayed here when connected to the database.*")

    # # Placeholder alert history
    # placeholder_alerts = pd.DataFrame({
    #     "Date": ["2026-02-03", "2026-02-02", "2026-02-01"],
    #     "Type": ["Mention Spike", "Sentiment Drop", "Daily Summary"],
    #     "Keyword": ["matcha", "boba", "All"],
    #     "Status": ["Sent", "Sent", "Sent"]
    # })
    # st.dataframe(placeholder_alerts, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    st.title("🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")
    show_alerts_dashboard()
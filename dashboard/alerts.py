"""Manage user alerts."""

import os
import streamlit as st
import boto3


def login_prompt():
    """Prompt the user to log in if they are not already authenticated."""
    if not st.session_state.get("logged_in"):
        st.warning("Please log in to access the alerts dashboard.")
        st.stop()


def get_boto3_client():
    return boto3.client(
        'ses',
        region_name=os.getenv('AWS_REGION', 'eu-west-2'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
    )


def is_email_verified(client, email: str) -> bool:
    """Check if the email is verified with AWS SES."""
    response = client.list_verified_email_addresses()
    return email in response['VerifiedEmailAddresses']


def send_verification_email(client, email: str) -> dict:
    """Send a verification email to the specified address."""
    return client.verify_email_identity(EmailAddress=email)


def verify_email(client, email: str) -> bool:
    """Verify the email address and send verification if not already verified."""
    if is_email_verified(client, email):
        st.success(f"{email} is a verified email address.")
        return True
    else:
        st.info(f"Sending verification to {email}")
        send_verification_email(client, email)
        return False


def get_user_alert_settings(conn):
    """Fetch the user's current alert settings from the database."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT send_email, send_alert
            FROM users
            WHERE email = %s
        """, (st.session_state.email,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        else:
            return False, False


def update_users_settings(conn, emails_enabled: bool, alerts_enabled: bool):
    """Update the user's alert settings in the database."""
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE users
            SET send_email = %s, send_alert = %s
            WHERE email = %s
        """, (emails_enabled, alerts_enabled, st.session_state.email))
        conn.commit()


def email_toggle_on_change(conn, client):
    """Handle changes to the email toggle."""
    if st.session_state.emails_enabled:
        if not is_email_verified(client, st.session_state.email):
            st.error("Please verify your email before enabling this feature.")
            return
    update_users_settings(
        conn, st.session_state.emails_enabled, st.session_state.alerts_enabled)


def alert_toggle_on_change(conn, client):
    """Handle changes to the alert toggle."""
    if st.session_state.alerts_enabled:
        if not is_email_verified(client, st.session_state.email):
            st.error("Please verify your email before enabling this feature.")
            return
    update_users_settings(
        conn, st.session_state.emails_enabled, st.session_state.alerts_enabled)


def gen_email_toggle(conn, client, value: bool):
    """Generate email toggle"""
    return st.toggle(
        "Enable Email Reports",
        value=value,
        key="emails_enabled",
        on_change=email_toggle_on_change,
        args=(conn, client),
        help="Receive a weekly email summary of trends and insights based on your keywords"
    )


def gen_alert_toggle(conn, client, value: bool):
    """Generate alert toggle"""
    return st.toggle(
        "Enable Spike Alerts",
        value=value,
        key="alerts_enabled",
        on_change=alert_toggle_on_change,
        args=(conn, client),
        help="Receive alerts for significant trend changes"
    )


def show_alerts_dashboard(conn, emails_value: bool, alerts_value: bool):
    """Display the alerts/notifications management dashboard."""

    st.markdown("---")
    st.markdown("### 📧 Email Weekly Reports")

    client = get_boto3_client()

    # Check verification status upfront
    is_verified = is_email_verified(client, st.session_state.email)
    if not is_verified:
        st.info(
            f"📬 Your email ({st.session_state.email}) is not yet verified. Sending verification email...")
        send_verification_email(client, st.session_state.email)
    else:
        st.success(f"✅ Email verified: {st.session_state.email}")

    st.markdown("")

    # Create toggles - only enable if email is verified
    if is_verified:
        gen_email_toggle(conn, client, emails_value)
        gen_alert_toggle(conn, client, alerts_value)
    else:
        st.toggle(
            "Enable Email Reports",
            value=False,
            disabled=True,
            help="Verify your email first to enable this feature"
        )
        st.toggle(
            "Enable Spike Alerts",
            value=False,
            disabled=True,
            help="Verify your email first to enable this feature"
        )

    st.markdown("---")


def render_alerts_dashboard(conn):
    """Render the alerts dashboard content."""
    login_prompt()

    st.markdown("### 🔔 Alerts & Notifications")
    st.markdown("Configure your alert preferences and notification settings.")

    # Fetch database values and pass them to show_alerts_dashboard
    emails, alerts = get_user_alert_settings(conn)
    show_alerts_dashboard(conn, emails, alerts)


if __name__ == "__main__":
    pass

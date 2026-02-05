import streamlit as st
import boto3


def verify_email(email: str) -> bool:
    """Check if user is verified on AWS with boto3."""
    ses = boto3.client("ses", region_name="eu-west-2")

    response = ses.get_identity_verification_attributes(
        Identities=[email]
    )
    status = response["VerificationAttributes"][email]["VerificationStatus"]
    
    if status == "Success":
        return True
    elif status == "Pending":
        st.warning(f"Email {email} is pending verification. Please check your inbox and verify to receive alerts.")
        return False
    else:
        st.error(f"Email {email} is not verified. Please verify your email to receive alerts.")
        return False


def show_alerts_dashboard():
    """Display the alerts/notifications management dashboard."""

    st.markdown("---")

    # Email alerts section
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
    print(st.session_state["emails_enabled"], st.session_state["alerts_enabled"])
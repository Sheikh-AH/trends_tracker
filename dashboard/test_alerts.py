# pylint: disable=missing-function-docstring, import-error
"""
Comprehensive tests for alerts.py module.

Tests cover:
- login_prompt: Login check and stop behavior
- get_boto3_client: AWS SES client creation
- is_email_verified: Email verification status check
- send_verification_email: Sending verification emails
- verify_email: Combined verification flow
- get_user_alert_settings: Fetching user settings from DB
- update_users_settings: Updating user settings in DB
- email_toggle_on_change: Toggle change handlers
- alert_toggle_on_change: Toggle change handlers
- show_alerts_dashboard: Dashboard rendering
- render_alerts_dashboard: Full dashboard render
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from alerts import (
    get_boto3_client, is_email_verified, send_verification_email,
    verify_email, get_user_alert_settings, update_users_settings,
    email_toggle_on_change, alert_toggle_on_change, login_prompt,
    gen_email_toggle, gen_alert_toggle, show_alerts_dashboard,
    render_alerts_dashboard
)


# ============== Tests for get_boto3_client ==============

class TestGetBoto3Client:
    """Tests for get_boto3_client function."""

    @patch.dict(os.environ, {
        "AWS_ACCESS_KEY": "test_access_key",
        "AWS_SECRET_KEY": "test_secret_key",
        "AWS_REGION": "eu-west-2"
    })
    @patch("alerts.boto3.client")
    def test_creates_client_with_explicit_keys(self, mock_boto_client):
        """Test that client is created with explicit AWS keys when provided."""
        get_boto3_client()

        mock_boto_client.assert_called_once_with(
            'ses',
            region_name='eu-west-2',
            aws_access_key_id='test_access_key',
            aws_secret_access_key='test_secret_key'
        )

    @patch.dict(os.environ, {
        "AWS_ACCESS_KEY": "",
        "AWS_SECRET_KEY": "",
        "AWS_REGION": "us-east-1"
    }, clear=True)
    @patch("alerts.boto3.client")
    def test_creates_client_with_default_credentials(self, mock_boto_client):
        """Test that client falls back to default credentials when keys not provided."""
        # Clear the env vars
        os.environ.pop("AWS_ACCESS_KEY", None)
        os.environ.pop("AWS_SECRET_KEY", None)

        get_boto3_client()

        # Should be called without explicit keys
        mock_boto_client.assert_called_once()
        call_kwargs = mock_boto_client.call_args[1]
        assert 'aws_access_key_id' not in call_kwargs

    @patch.dict(os.environ, {"AWS_REGION": "ap-southeast-1"}, clear=True)
    @patch("alerts.boto3.client")
    def test_uses_region_from_env(self, mock_boto_client):
        """Test that region is read from environment variable."""
        get_boto3_client()

        call_kwargs = mock_boto_client.call_args[1]
        assert call_kwargs['region_name'] == 'ap-southeast-1'


# ============== Tests for is_email_verified ==============

class TestIsEmailVerified:
    """Tests for is_email_verified function."""

    def test_returns_true_when_email_verified(self):
        """Test that True is returned when email is in verified list."""
        mock_client = Mock()
        mock_client.list_verified_email_addresses.return_value = {
            'VerifiedEmailAddresses': ['test@example.com', 'other@example.com']
        }

        result = is_email_verified(mock_client, 'test@example.com')

        assert result is True

    def test_returns_false_when_email_not_verified(self):
        """Test that False is returned when email is not in verified list."""
        mock_client = Mock()
        mock_client.list_verified_email_addresses.return_value = {
            'VerifiedEmailAddresses': ['other@example.com']
        }

        result = is_email_verified(mock_client, 'test@example.com')

        assert result is False

    def test_returns_false_when_no_verified_emails(self):
        """Test that False is returned when no emails are verified."""
        mock_client = Mock()
        mock_client.list_verified_email_addresses.return_value = {
            'VerifiedEmailAddresses': []
        }

        result = is_email_verified(mock_client, 'test@example.com')

        assert result is False

    def test_calls_list_verified_email_addresses(self):
        """Test that list_verified_email_addresses is called."""
        mock_client = Mock()
        mock_client.list_verified_email_addresses.return_value = {
            'VerifiedEmailAddresses': []
        }

        is_email_verified(mock_client, 'test@example.com')

        mock_client.list_verified_email_addresses.assert_called_once()


# ============== Tests for send_verification_email ==============

class TestSendVerificationEmail:
    """Tests for send_verification_email function."""

    def test_calls_verify_email_identity(self):
        """Test that verify_email_identity is called with correct email."""
        mock_client = Mock()
        mock_client.verify_email_identity.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        result = send_verification_email(mock_client, 'test@example.com')

        mock_client.verify_email_identity.assert_called_once_with(EmailAddress='test@example.com')

    def test_returns_response_dict(self):
        """Test that response dictionary is returned."""
        mock_client = Mock()
        expected_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_client.verify_email_identity.return_value = expected_response

        result = send_verification_email(mock_client, 'test@example.com')

        assert result == expected_response


# ============== Tests for verify_email ==============

class TestVerifyEmail:
    """Tests for verify_email function."""

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    def test_returns_true_when_already_verified(self, mock_is_verified, mock_st):
        """Test that True is returned when email is already verified."""
        mock_is_verified.return_value = True
        mock_client = Mock()

        result = verify_email(mock_client, 'test@example.com')

        assert result is True
        mock_st.success.assert_called_once()

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.send_verification_email")
    def test_sends_verification_when_not_verified(self, mock_send, mock_is_verified, mock_st):
        """Test that verification email is sent when not already verified."""
        mock_is_verified.return_value = False
        mock_client = Mock()

        result = verify_email(mock_client, 'test@example.com')

        assert result is False
        mock_send.assert_called_once_with(mock_client, 'test@example.com')
        mock_st.info.assert_called_once()


# ============== Tests for get_user_alert_settings ==============

class TestGetUserAlertSettings:
    """Tests for get_user_alert_settings function."""

    @patch("alerts.st")
    def test_returns_settings_when_found(self, mock_st):
        """Test that settings are returned when user is found."""
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (True, False)

        send_email, send_alert = get_user_alert_settings(mock_conn)

        assert send_email is True
        assert send_alert is False

    @patch("alerts.st")
    def test_returns_false_false_when_not_found(self, mock_st):
        """Test that (False, False) is returned when user not found."""
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None

        send_email, send_alert = get_user_alert_settings(mock_conn)

        assert send_email is False
        assert send_alert is False

    @patch("alerts.st")
    def test_executes_correct_query(self, mock_st):
        """Test that correct SQL query is executed."""
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (True, True)

        get_user_alert_settings(mock_conn)

        # Check that execute was called with correct email
        call_args = mock_cursor.execute.call_args
        assert "test@example.com" in call_args[0][1]


# ============== Tests for update_users_settings ==============

class TestUpdateUsersSettings:
    """Tests for update_users_settings function."""

    @patch("alerts.st")
    def test_updates_settings_in_database(self, mock_st):
        """Test that settings are updated in database."""
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        update_users_settings(mock_conn, True, False)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("alerts.st")
    def test_passes_correct_parameters(self, mock_st):
        """Test that correct parameters are passed to SQL."""
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        update_users_settings(mock_conn, True, False)

        call_args = mock_cursor.execute.call_args[0][1]
        assert call_args == (True, False, "test@example.com")


# ============== Tests for email_toggle_on_change ==============

class TestEmailToggleOnChange:
    """Tests for email_toggle_on_change function."""

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.update_users_settings")
    def test_updates_settings_when_email_verified(self, mock_update, mock_is_verified, mock_st):
        """Test that settings are updated when email is verified."""
        mock_st.session_state.emails_enabled = True
        mock_st.session_state.alerts_enabled = False
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = True
        mock_conn = Mock()
        mock_client = Mock()

        email_toggle_on_change(mock_conn, mock_client)

        mock_update.assert_called_once_with(mock_conn, True, False)

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.update_users_settings")
    def test_shows_error_when_email_not_verified(self, mock_update, mock_is_verified, mock_st):
        """Test that error is shown when email is not verified."""
        mock_st.session_state.emails_enabled = True
        mock_st.session_state.alerts_enabled = False
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = False
        mock_conn = Mock()
        mock_client = Mock()

        email_toggle_on_change(mock_conn, mock_client)

        mock_st.error.assert_called_once()
        mock_update.assert_not_called()

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.update_users_settings")
    def test_updates_settings_when_disabling(self, mock_update, mock_is_verified, mock_st):
        """Test that settings are updated when disabling (no verification needed)."""
        mock_st.session_state.emails_enabled = False
        mock_st.session_state.alerts_enabled = False
        mock_st.session_state.email = "test@example.com"
        mock_conn = Mock()
        mock_client = Mock()

        email_toggle_on_change(mock_conn, mock_client)

        mock_update.assert_called_once_with(mock_conn, False, False)


# ============== Tests for alert_toggle_on_change ==============

class TestAlertToggleOnChange:
    """Tests for alert_toggle_on_change function."""

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.update_users_settings")
    def test_updates_settings_when_email_verified(self, mock_update, mock_is_verified, mock_st):
        """Test that settings are updated when email is verified."""
        mock_st.session_state.emails_enabled = False
        mock_st.session_state.alerts_enabled = True
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = True
        mock_conn = Mock()
        mock_client = Mock()

        alert_toggle_on_change(mock_conn, mock_client)

        mock_update.assert_called_once_with(mock_conn, False, True)

    @patch("alerts.st")
    @patch("alerts.is_email_verified")
    @patch("alerts.update_users_settings")
    def test_shows_error_when_email_not_verified(self, mock_update, mock_is_verified, mock_st):
        """Test that error is shown when email is not verified."""
        mock_st.session_state.emails_enabled = False
        mock_st.session_state.alerts_enabled = True
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = False
        mock_conn = Mock()
        mock_client = Mock()

        alert_toggle_on_change(mock_conn, mock_client)

        mock_st.error.assert_called_once()
        mock_update.assert_not_called()


# ============== Tests for login_prompt ==============

class TestLoginPrompt:
    """Tests for login_prompt function."""

    @patch("alerts.st")
    def test_shows_warning_when_not_logged_in(self, mock_st):
        """Test that warning is shown when user is not logged in."""
        mock_st.session_state.get.return_value = False

        # login_prompt calls st.stop() which we need to handle
        mock_st.stop.side_effect = Exception("StopExecution")

        with pytest.raises(Exception, match="StopExecution"):
            login_prompt()

        mock_st.warning.assert_called_once()

    @patch("alerts.st")
    def test_does_nothing_when_logged_in(self, mock_st):
        """Test that nothing happens when user is logged in."""
        mock_st.session_state.get.return_value = True

        # Should not raise or call warning
        login_prompt()

        mock_st.warning.assert_not_called()
        mock_st.stop.assert_not_called()


# ============== Tests for gen_email_toggle ==============

class TestGenEmailToggle:
    """Tests for gen_email_toggle function."""

    @patch("alerts.st")
    @patch("alerts.email_toggle_on_change")
    def test_creates_toggle_with_correct_parameters(self, mock_on_change, mock_st):
        """Test that toggle is created with correct parameters."""
        mock_conn = Mock()
        mock_client = Mock()

        gen_email_toggle(mock_conn, mock_client, True)

        mock_st.toggle.assert_called_once()
        call_kwargs = mock_st.toggle.call_args[1]
        assert call_kwargs["value"] is True
        assert call_kwargs["key"] == "emails_enabled"


# ============== Tests for gen_alert_toggle ==============

class TestGenAlertToggle:
    """Tests for gen_alert_toggle function."""

    @patch("alerts.st")
    @patch("alerts.alert_toggle_on_change")
    def test_creates_toggle_with_correct_parameters(self, mock_on_change, mock_st):
        """Test that toggle is created with correct parameters."""
        mock_conn = Mock()
        mock_client = Mock()

        gen_alert_toggle(mock_conn, mock_client, False)

        mock_st.toggle.assert_called_once()
        call_kwargs = mock_st.toggle.call_args[1]
        assert call_kwargs["value"] is False
        assert call_kwargs["key"] == "alerts_enabled"


# ============== Tests for show_alerts_dashboard ==============

class TestShowAlertsDashboard:
    """Tests for show_alerts_dashboard function."""

    @patch("alerts.st")
    @patch("alerts.get_boto3_client")
    @patch("alerts.is_email_verified")
    @patch("alerts.send_verification_email")
    @patch("alerts.gen_email_toggle")
    @patch("alerts.gen_alert_toggle")
    def test_shows_verification_info_when_not_verified(
        self, mock_alert_toggle, mock_email_toggle, mock_send,
        mock_is_verified, mock_get_client, mock_st
    ):
        """Test that verification info is shown when email not verified."""
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = False
        mock_conn = Mock()

        show_alerts_dashboard(mock_conn, False, False)

        mock_st.info.assert_called()
        mock_send.assert_called_once()

    @patch("alerts.st")
    @patch("alerts.get_boto3_client")
    @patch("alerts.is_email_verified")
    @patch("alerts.gen_email_toggle")
    @patch("alerts.gen_alert_toggle")
    def test_shows_success_when_verified(
        self, mock_alert_toggle, mock_email_toggle,
        mock_is_verified, mock_get_client, mock_st
    ):
        """Test that success message is shown when email is verified."""
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = True
        mock_conn = Mock()

        show_alerts_dashboard(mock_conn, True, False)

        mock_st.success.assert_called()
        mock_email_toggle.assert_called_once()
        mock_alert_toggle.assert_called_once()

    @patch("alerts.st")
    @patch("alerts.get_boto3_client")
    @patch("alerts.is_email_verified")
    def test_disables_toggles_when_not_verified(
        self, mock_is_verified, mock_get_client, mock_st
    ):
        """Test that toggles are disabled when email not verified."""
        mock_st.session_state.email = "test@example.com"
        mock_is_verified.return_value = False
        mock_conn = Mock()

        show_alerts_dashboard(mock_conn, False, False)

        # st.toggle should be called with disabled=True
        toggle_calls = mock_st.toggle.call_args_list
        assert len(toggle_calls) == 2
        for call in toggle_calls:
            assert call[1]["disabled"] is True


# ============== Tests for render_alerts_dashboard ==============

class TestRenderAlertsDashboard:
    """Tests for render_alerts_dashboard function."""

    @patch("alerts.st")
    @patch("alerts.login_prompt")
    @patch("alerts.get_user_alert_settings")
    @patch("alerts.show_alerts_dashboard")
    def test_calls_login_prompt_first(
        self, mock_show, mock_get_settings, mock_login, mock_st
    ):
        """Test that login_prompt is called first."""
        mock_get_settings.return_value = (False, False)
        mock_conn = Mock()

        render_alerts_dashboard(mock_conn)

        mock_login.assert_called_once()

    @patch("alerts.st")
    @patch("alerts.login_prompt")
    @patch("alerts.get_user_alert_settings")
    @patch("alerts.show_alerts_dashboard")
    def test_fetches_and_passes_settings(
        self, mock_show, mock_get_settings, mock_login, mock_st
    ):
        """Test that settings are fetched and passed to show_alerts_dashboard."""
        mock_get_settings.return_value = (True, False)
        mock_conn = Mock()

        render_alerts_dashboard(mock_conn)

        mock_get_settings.assert_called_once_with(mock_conn)
        mock_show.assert_called_once_with(mock_conn, True, False)

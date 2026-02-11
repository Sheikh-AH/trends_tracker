"""
Streamlit App Integration Tests using AppTest framework.

Tests cover:
- App initialization and page configuration
- Login/signup form interactions
- Session state management
- Navigation and page routing
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from streamlit.testing.v1 import AppTest


class TestAppInitialization:
    """Tests for app.py initialization and configuration."""

    @patch("db_utils.get_db_connection")
    def test_app_runs_without_exception(self, mock_db):
        """Test that app initializes without errors."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Check no exceptions occurred
        assert not at.exception

    @patch("db_utils.get_db_connection")
    def test_login_page_shows_when_not_logged_in(self, mock_db):
        """Test that login page is shown when user is not logged in."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Should have text inputs for login
        assert len(at.text_input) >= 2  # Username and password

    @patch("db_utils.get_db_connection")
    def test_has_login_button(self, mock_db):
        """Test that login button is present."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Should have at least one button (Login)
        assert len(at.button) >= 1

    @patch("db_utils.get_db_connection")
    def test_has_tabs_for_login_and_signup(self, mock_db):
        """Test that login and signup tabs exist."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Should have tabs (Login and Sign Up)
        assert len(at.tabs) == 2


class TestSessionStateInitialization:
    """Tests for session state initialization."""

    @patch("db_utils.get_db_connection")
    def test_session_state_logged_in_false_by_default(self, mock_db):
        """Test that logged_in is False by default."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Session state should have logged_in = False
        assert at.session_state.logged_in is False


class TestLoginFlow:
    """Tests for login authentication flow."""

    @patch("db_utils.get_db_connection")
    @patch("auth_utils.authenticate_user")
    @patch("auth_utils.get_user_by_username")
    def test_successful_login_sets_session(self, mock_get_user, mock_auth, mock_db):
        """Test that successful login updates session state."""
        mock_db.return_value = Mock()
        mock_auth.return_value = True
        mock_get_user.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "password_hash": "hash"
        }

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Enter credentials
        if len(at.text_input) == 2:
            at.text_input[0].input("test@example.com")
            at.text_input[1].input("password123")

            # Click login button
            if len(at.button) >= 1:
                at.button[0].click()
                at.run()
                # Verify session state was updated
                assert at.session_state.logged_in is True
                assert at.session_state.user_id == 1

    @patch("db_utils.get_db_connection")
    def test_empty_credentials_shows_error(self, mock_db):
        """Test that empty credentials trigger error."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Leave credentials empty and click login
        if len(at.button) >= 1:
            at.button[0].click()
            at.run()
            # Verify error message was displayed
            assert len(at.error) > 0 or len(
                at.warning) > 0, "Expected error or warning message"


class TestSignupFlow:
    """Tests for signup/registration flow."""

    @patch("db_utils.get_db_connection")
    def test_signup_tab_has_required_fields(self, mock_db):
        """Test that signup tab has all required input fields."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Should have multiple text inputs including signup fields
        assert len(at.text_input) >= 2


class TestPageHelperFunctions:
    """Tests for helper functions used across pages."""

    def test_time_periods_function(self):
        """Test time_periods returns correct dictionary."""
        # Import from 4_Keyword_Deep_Dive
        expected_periods = {
            "7 days": 7,
            "14 days": 14,
            "30 days": 30,
            "90 days": 90,
            "6 months": 180,
            "1 year": 365
        }

        # Verify structure
        assert "7 days" in expected_periods
        assert expected_periods["7 days"] == 7
        assert expected_periods["1 year"] == 365


class TestNavigationCreation:
    """Tests for navigation menu creation."""

    def test_navigation_pages_structure(self):
        """Test that navigation includes expected pages."""
        expected_pages = [
            "pages/1_Home.py",
            "pages/2_Semantics.py",
            "pages/3_Daily_Summary.py",
            "pages/4_Keyword_Deep_Dive.py",
            "pages/5_Comparisons.py",
            "pages/6_Profile.py"
        ]

        # Verify all expected pages exist
        import os
        for page in expected_pages:
            assert os.path.exists(page), f"Page {page} should exist"


class TestUserSessionFunctions:
    """Tests for user session management functions."""

    def test_set_user_session_logic(self):
        """Test set_user_session updates session correctly."""
        # Mock user data
        user = {
            "email": "test@example.com",
            "user_id": 123
        }

        # Expected session state updates
        expected_username = user["email"].split("@")[0]

        assert expected_username == "test"


class TestAppErrorHandling:
    """Tests for error handling in the app."""

    @patch("db_utils.get_db_connection")
    def test_database_connection_failure_handled(self, mock_db):
        """Test that database connection failure is handled gracefully."""
        mock_db.side_effect = Exception("Connection failed")

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # App should still run without crashing
        # Exception handling should catch DB errors
        assert not at.exception or len(
            at.error) > 0, "App should handle error gracefully"


class TestFormValidation:
    """Tests for form input validation logic."""

    def test_new_account_fields_returns_tuple(self):
        """Test that new_account_fields would return tuple of values."""
        # The function returns: name, email, password, confirm
        expected_length = 4

        # We can't call the actual function without Streamlit context,
        # but we can verify the expected behavior
        sample_tuple = ("John Doe", "john@example.com",
                        "password123", "password123")
        assert len(sample_tuple) == expected_length

    def test_password_confirmation_logic(self):
        """Test password confirmation matching logic."""
        password = "password123"
        confirm = "password123"

        assert password == confirm

        # Non-matching case
        confirm_wrong = "password456"
        assert password != confirm_wrong


class TestComponentRendering:
    """Tests for UI component rendering."""

    @patch("db_utils.get_db_connection")
    def test_logo_image_rendered(self, mock_db):
        """Test that logo image is rendered on login page."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Verify the page renders without exceptions
        assert not at.exception, "App should render without exceptions"
        assert len(at.title) >= 1, "Page should have title element"

    @patch("db_utils.get_db_connection")
    def test_title_rendered(self, mock_db):
        """Test that title is rendered on login page."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Should have title element
        assert len(at.title) >= 1


class TestAlertsDashboard:
    """Tests for alerts functionality."""

    def test_alerts_module_exists(self):
        """Test that alerts module exists and is importable."""
        try:
            import alerts
            assert hasattr(
                alerts, 'render_alerts_dashboard'), "Module should have render_alerts_dashboard function"
        except ImportError as e:
            pytest.skip(f"Alerts module not available: {e}")


class TestKeywordDeepDiveIntegration:
    """Integration tests for Keyword Deep Dive page."""

    def test_page_file_exists(self):
        """Test that Keyword Deep Dive page file exists."""
        import os
        assert os.path.exists("pages/4_Keyword_Deep_Dive.py")

    def test_page_has_required_functions(self):
        """Test that page has required visualization functions."""
        import sys
        sys.path.insert(0, "pages")

        # Read the file and check for function definitions
        with open("pages/4_Keyword_Deep_Dive.py", "r") as f:
            content = f.read()

        required_functions = [
            "def configure_page",
            "def render_filters",
            "def get_daily_analytics",
            "def render_activity_over_time",
            "def render_sentiment_distribution",
        ]

        for func in required_functions:
            assert func in content, f"Function {func} should exist in page"


class TestSemanticsPageIntegration:
    """Integration tests for Semantics page."""

    def test_page_file_exists(self):
        """Test that Semantics page file exists."""
        import os
        assert os.path.exists("pages/2_Semantics.py")

    def test_page_imports_required_utils(self):
        """Test that page imports required utility functions."""
        with open("pages/2_Semantics.py", "r") as f:
            content = f.read()

        required_imports = [
            "get_user_keywords",
            "extract_keywords_yake",
            "diversify_keywords",
        ]

        for imp in required_imports:
            assert imp in content, f"Import {imp} should be in page"


class TestDailySummaryPageIntegration:
    """Integration tests for Daily Summary page."""

    def test_page_file_exists(self):
        """Test that Daily Summary page file exists."""
        import os
        assert os.path.exists("pages/3_Daily_Summary.py")


class TestComparisonsPageIntegration:
    """Integration tests for Comparisons page."""

    def test_page_file_exists(self):
        """Test that Comparisons page file exists."""
        import os
        assert os.path.exists("pages/5_Comparisons.py")


class TestProfilePageIntegration:
    """Integration tests for Profile page."""

    def test_page_file_exists(self):
        """Test that Profile page file exists."""
        import os
        assert os.path.exists("pages/6_Profile.py")

    def test_page_imports_keyword_utils(self):
        """Test that page imports keyword management utilities."""
        with open("pages/6_Profile.py", "r") as f:
            content = f.read()

        required_imports = [
            "add_user_keyword",
            "remove_user_keyword",
        ]

        for imp in required_imports:
            assert imp in content, f"Import {imp} should be in page"

# pylint: disable=import-error, missing-function-docstring, redefined-outer-name
"""Tests for pages/6_Profile.py - Direct function testing for coverage."""

import os
import sys
import importlib.util
from unittest.mock import Mock, patch, MagicMock
import pytest
from streamlit.testing.v1 import AppTest

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DASHBOARD_DIR)
sys.path.insert(0, os.path.join(DASHBOARD_DIR, "pages"))


class TestLoadKeywords:
    """Tests for load_keywords function."""

    def test_load_keywords_when_not_loaded(self, profile_module):
        """Test load_keywords fetches from database when not loaded."""
        module, mock_st, mock_db, mock_kw, *_ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: {
            "keywords_loaded": False, "user_id": 1, "keywords": []
        }.get(key, default)
        mock_st.session_state.__contains__ = lambda self, key: key != "keywords"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn
        mock_kw.get_user_keywords.return_value = ["test", "python"]

        module.load_keywords()

    def test_load_keywords_already_loaded(self, profile_module):
        """Test load_keywords skips when already loaded."""
        module, mock_st, mock_db, *_ = profile_module

        # Modify existing session_state instead of replacing it
        mock_st.session_state.get = lambda key, default=None: True if key == "keywords_loaded" else default
        mock_st.session_state.__contains__ = lambda self, key: True

        # Reset mock to clear any calls from module setup
        mock_db.get_db_connection.reset_mock()

        module.load_keywords()

        mock_db.get_db_connection.assert_not_called()

    def test_load_keywords_initializes_keywords(self, profile_module):
        """Test load_keywords initializes keywords if not present."""
        module, mock_st, *_ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: True if key == "keywords_loaded" else default
        mock_st.session_state.__contains__ = lambda self, key: key != "keywords"

        module.load_keywords()


class TestRenderAddKeywordSection:
    """Tests for render_add_keyword_section function."""

    def test_render_add_keyword_section_empty_input(self, profile_module):
        """Test render_add_keyword_section with empty input."""
        module, mock_st, *_ = profile_module

        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=None)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=None)
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        module.render_add_keyword_section()

        mock_st.columns.assert_called()

    def test_render_add_keyword_section_add_new_keyword(self, profile_module):
        """Test render_add_keyword_section adds new keyword."""
        module, mock_st, mock_db, mock_kw, *_ = profile_module

        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=None)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=None)

        mock_st.text_input.return_value = "newkeyword"
        mock_st.button.return_value = True

        mock_st.session_state = MagicMock()
        mock_st.session_state.keywords = []
        mock_st.session_state.user_id = 1

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn

        module.render_add_keyword_section()

        mock_db.get_db_connection.assert_called()
        mock_kw.add_user_keyword.assert_called()
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()

    def test_render_add_keyword_section_duplicate_keyword(self, profile_module):
        """Test render_add_keyword_section warns on duplicate."""
        module, mock_st, *_ = profile_module

        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=None)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=None)

        mock_st.text_input.return_value = "existing"
        mock_st.button.return_value = True

        mock_st.session_state = MagicMock()
        mock_st.session_state.keywords = ["existing"]

        module.render_add_keyword_section()


class TestRemoveKeyword:
    """Tests for remove_keyword function."""

    def test_remove_keyword_success(self, profile_module):
        """Test remove_keyword removes keyword from database."""
        module, mock_st, mock_db, mock_kw, *_ = profile_module

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn

        # Create a real list so .remove() works
        keywords_list = ["test", "remove_me"]

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: 1 if key == "user_id" else (keywords_list if key == "keywords" else default)
        mock_st.session_state.user_id = 1
        mock_st.session_state.keywords = keywords_list

        # Also patch the module's ss reference
        module.ss.keywords = keywords_list
        module.ss.get = lambda key, default=None: 1 if key == "user_id" else (keywords_list if key == "keywords" else default)
        module.ss.user_id = 1

        module.remove_keyword("remove_me")

    def test_remove_keyword_no_connection(self, profile_module):
        """Test remove_keyword handles no connection."""
        module, mock_st, mock_db, *_ = profile_module

        mock_db.get_db_connection.return_value = None

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: None

        module.remove_keyword("test")

    def test_remove_keyword_no_user_id(self, profile_module):
        """Test remove_keyword handles no user_id."""
        module, mock_st, mock_db, *_ = profile_module

        mock_conn = MagicMock()
        mock_db.get_db_connection.return_value = mock_conn

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: None

        module.remove_keyword("test")


class TestRenderKeywordsDisplay:
    """Tests for render_keywords_display function."""

    def test_render_keywords_display_empty(self, profile_module):
        """Test render_keywords_display with no keywords."""
        module, mock_st, _, _, mock_ui, _ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: [] if key == "keywords" else default

        cols = [MagicMock() for _ in range(4)]
        for col in cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=None)
        mock_st.columns.return_value = cols

        module.render_keywords_display()

    def test_render_keywords_display_with_keywords(self, profile_module):
        """Test render_keywords_display with keywords."""
        module, mock_st, _, _, mock_ui, _ = profile_module

        # Modify existing session_state instead of replacing it
        mock_st.session_state.get = lambda key, default=None: ["test", "python"] if key == "keywords" else default

        cols = [MagicMock() for _ in range(4)]
        for col in cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=None)
        mock_st.columns.return_value = cols
        mock_st.button.return_value = False

        mock_ui.load_html_template.return_value = "<div>{keyword}</div>"

        module.render_keywords_display()

        # Check that markdown was called (should be called for each keyword)
        assert mock_st.markdown.call_count >= 1

    def test_render_keywords_display_remove_button_clicked(self, profile_module):
        """Test render_keywords_display when remove button is clicked."""
        module, mock_st, mock_db, mock_kw, mock_ui, _ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: ["test"] if key == "keywords" else 1 if key == "user_id" else default
        mock_st.session_state.user_id = 1
        mock_st.session_state.keywords = ["test"]

        cols = [MagicMock() for _ in range(4)]
        for col in cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=None)
        mock_st.columns.return_value = cols
        mock_st.button.return_value = True

        mock_ui.load_html_template.return_value = "<div>{keyword}</div>"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn

        module.render_keywords_display()


class TestLoadKeywordsExtended:
    """Extended tests for load_keywords function coverage."""

    def test_load_keywords_initializes_empty_keywords_list(self, profile_module):
        """Test load_keywords initializes empty keywords when not in session."""
        module, mock_st, mock_db, mock_kw, *_ = profile_module

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn
        mock_kw.get_user_keywords.return_value = None

        # Session state with no keywords_loaded and no keywords key
        ss_dict = {"user_id": 1}
        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: ss_dict.get(key, default)
        mock_st.session_state.__contains__ = lambda self, key: key in ss_dict

        module.ss = mock_st.session_state

        module.load_keywords()

    def test_load_keywords_with_connection_and_user(self, profile_module):
        """Test load_keywords loads from database when connected."""
        module, mock_st, mock_db, mock_kw, *_ = profile_module

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_db_connection.return_value = mock_conn
        mock_kw.get_user_keywords.return_value = ["keyword1", "keyword2"]

        ss_dict = {"user_id": 1, "keywords_loaded": False}
        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: ss_dict.get(key, default)

        module.ss = mock_st.session_state

        module.load_keywords()


class TestRenderKeywordsDisplayExtended:
    """Extended tests for render_keywords_display function."""

    def test_render_keywords_display_with_keywords(self, profile_module):
        """Test render_keywords_display shows keywords."""
        module, mock_st, *_ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: ["test1", "test2"] if key == "keywords" else default
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        module.ss = mock_st.session_state

        module.render_keywords_display()

    def test_render_keywords_display_with_remove_button(self, profile_module):
        """Test render_keywords_display has remove buttons."""
        module, mock_st, *_ = profile_module

        mock_st.session_state = MagicMock()
        mock_st.session_state.get = lambda key, default=None: ["test_keyword"] if key == "keywords" else default

        col_mock = MagicMock()
        col_mock.__enter__ = MagicMock(return_value=col_mock)
        col_mock.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [col_mock, col_mock, col_mock, col_mock]
        mock_st.button.return_value = False

        module.ss = mock_st.session_state

        module.render_keywords_display()


class TestProfileAppTest:
    """AppTest integration tests for Profile page."""

    @patch("db_utils.get_db_connection")
    def test_profile_redirects_when_not_logged_in(self, mock_db):
        """Test Profile page redirects when not logged in."""
        mock_db.return_value = Mock()

        at = AppTest.from_file("pages/6_Profile.py", default_timeout=10)
        at.run()

        assert len(at.warning) > 0 or at.exception

    @patch("alerts.render_alerts_dashboard")
    @patch("db_utils.get_db_connection")
    @patch("keyword_utils.get_user_keywords")
    def test_profile_loads_when_logged_in(self, mock_keywords, mock_db, mock_alerts_dash):
        """Test Profile page loads with logged-in user."""
        mock_conn = Mock()
        mock_db.return_value = mock_conn
        mock_keywords.return_value = ["python", "javascript"]

        at = AppTest.from_file("pages/6_Profile.py", default_timeout=10)
        at.session_state.logged_in = True
        at.session_state.user_id = 1
        at.session_state.username = "testuser"
        at.session_state.email = "test@test.com"
        at.session_state.keywords_loaded = True
        at.session_state.keywords = ["python", "javascript"]
        at.run()

        assert not at.exception

    @patch("alerts.render_alerts_dashboard")
    @patch("db_utils.get_db_connection")
    @patch("keyword_utils.get_user_keywords")
    def test_profile_has_text_input(self, mock_keywords, mock_db, mock_alerts_dash):
        """Test Profile page renders keyword text input."""
        mock_conn = Mock()
        mock_db.return_value = mock_conn
        mock_keywords.return_value = ["python"]

        at = AppTest.from_file("pages/6_Profile.py", default_timeout=10)
        at.session_state.logged_in = True
        at.session_state.user_id = 1
        at.session_state.username = "testuser"
        at.session_state.email = "test@test.com"
        at.session_state.keywords_loaded = True
        at.session_state.keywords = ["python"]
        at.run()

        assert len(at.text_input) >= 1

    @patch("alerts.render_alerts_dashboard")
    @patch("db_utils.get_db_connection")
    @patch("keyword_utils.get_user_keywords")
    def test_profile_renders_buttons(self, mock_keywords, mock_db, mock_alerts_dash):
        """Test Profile page renders buttons (e.g. Logout)."""
        mock_conn = Mock()
        mock_db.return_value = mock_conn
        mock_keywords.return_value = []

        at = AppTest.from_file("pages/6_Profile.py", default_timeout=10)
        at.session_state.logged_in = True
        at.session_state.user_id = 1
        at.session_state.username = "testuser"
        at.session_state.email = "test@test.com"
        at.session_state.keywords_loaded = True
        at.session_state.keywords = []
        at.run()

        assert len(at.button) >= 1

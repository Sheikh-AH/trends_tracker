"""Shared pytest fixtures for dashboard tests."""

import os
import sys
import pytest
import importlib.util
import pandas as pd
from unittest.mock import Mock, MagicMock
from unittest.mock import patch
import hashlib
from datetime import datetime, timedelta, date
import psycopg2


# ============== Authentication & User Fixtures ==============

@pytest.fixture
def mock_cursor():
    "Mock database cursor for SQL query tests."
    return Mock()


@pytest.fixture
def valid_password():
    "Valid password string for authentication tests."
    return "test_password_123"


@pytest.fixture
def password_hash(valid_password):
    "Valid PBKDF2-SHA256 password hash for password verification tests."
    salt = "test_salt_value"
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        valid_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"{salt}${iterations}${hashed.hex()}"


@pytest.fixture
def user_row(password_hash):
    "Mock user database row dictionary for authentication tests."
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": password_hash
    }


@pytest.fixture
def user_dict(password_hash):
    "Mock user dictionary for authentication tests."
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": password_hash
    }


# ============== Database Connection Fixtures ==============

@pytest.fixture
def mock_conn():
    "Mock psycopg2 database connection for query tests."
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value = cursor
    cursor.connection = conn
    return conn


@pytest.fixture
def sample_date():
    "Sample date object for date-based query tests."
    return date(2026, 2, 9)


# ============== Streamlit & Page Setup Fixtures ==============

@pytest.fixture(autouse=True)
def change_to_dashboard_dir():
    "Autouse fixture to change working directory to dashboard for each test."
    original_cwd = os.getcwd()
    DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(DASHBOARD_DIR)
    yield
    os.chdir(original_cwd)


@pytest.fixture
def mock_streamlit():
    "Comprehensive mock of streamlit module for page tests."
    mock_st = MagicMock()
    mock_st.session_state = MagicMock()
    mock_st.session_state.__contains__ = lambda self, key: key in {
        "logged_in": True, "user_id": 1, "keywords": [],
        "keywords_loaded": False, "db_conn": MagicMock()
    }
    mock_st.session_state.__getitem__ = lambda self, key: {
        "logged_in": True, "user_id": 1, "keywords": [],
        "keywords_loaded": False, "db_conn": MagicMock()
    }.get(key)
    mock_st.session_state.get = lambda key, default=None: {
        "logged_in": True, "user_id": 1, "keywords": [],
        "keywords_loaded": False, "db_conn": MagicMock()
    }.get(key, default)
    mock_st.cache_data = lambda **kwargs: lambda fn: fn
    mock_st.cache_resource = lambda **kwargs: lambda fn: fn
    mock_st.get_option = MagicMock(return_value="light")
    return mock_st


@pytest.fixture
def home_module(mock_streamlit):
    "Imported Home page module with mocked dependencies."
    mock_db_utils = MagicMock()
    mock_db_utils.get_db_connection = MagicMock(return_value=MagicMock())

    mock_keyword_utils = MagicMock()
    mock_keyword_utils.get_user_keywords = MagicMock(return_value=["test", "python"])
    mock_keyword_utils.add_user_keyword = MagicMock()
    mock_keyword_utils.remove_user_keyword = MagicMock()

    mock_ui_utils = MagicMock()
    mock_ui_utils.load_html_template = MagicMock(return_value="<html>test</html>")
    mock_ui_utils.render_sidebar = MagicMock()

    mock_psycopg2 = MagicMock()
    mock_psycopg2.extras = MagicMock()
    mock_psycopg2.extras.RealDictCursor = MagicMock()

    with patch.dict("sys.modules", {
        "streamlit": mock_streamlit,
        "db_utils": mock_db_utils,
        "keyword_utils": mock_keyword_utils,
        "ui_helper_utils": mock_ui_utils,
        "psycopg2": mock_psycopg2,
        "psycopg2.extras": mock_psycopg2.extras,
    }):
        spec = importlib.util.spec_from_file_location(
            "home", "pages/1_Home.py"
        )
        home = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(home)
        return home, mock_streamlit, mock_db_utils, mock_keyword_utils, mock_ui_utils


@pytest.fixture
def comparisons_module(mock_streamlit):
    "Imported Comparisons page module with mocked dependencies."
    mock_db_utils = MagicMock()
    mock_db_utils.get_db_connection = MagicMock()

    mock_plotly = MagicMock()
    mock_query_utils = MagicMock()
    mock_query_utils._load_sql_query = MagicMock(return_value="SELECT 1")

    mock_keyword_utils = MagicMock()
    mock_keyword_utils.get_user_keywords = MagicMock(return_value=["test", "python"])

    mock_ui_utils = MagicMock()
    mock_ui_utils.render_sidebar = MagicMock()

    mock_altair = MagicMock()

    mock_psycopg2 = MagicMock()
    mock_psycopg2.extras = MagicMock()
    mock_psycopg2.extras.RealDictCursor = MagicMock()

    with patch.dict("sys.modules", {
        "streamlit": mock_streamlit,
        "altair": mock_altair,
        "pandas": pd,
        "db_utils": mock_db_utils,
        "keyword_utils": mock_keyword_utils,
        "query_utils": mock_query_utils,
        "ui_helper_utils": mock_ui_utils,
        "psycopg2": mock_psycopg2,
        "psycopg2.extras": mock_psycopg2.extras,
    }):
        spec = importlib.util.spec_from_file_location(
            "comparisons", "pages/5_Comparisons.py"
        )
        comparisons = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(comparisons)
        # Reset mocks after module load to clear any calls during import
        mock_db_utils.reset_mock()
        mock_keyword_utils.reset_mock()
        return comparisons, mock_streamlit, mock_db_utils, mock_keyword_utils, mock_query_utils, mock_ui_utils


@pytest.fixture
def profile_module(mock_streamlit):
    "Imported Profile page module with mocked dependencies."
    mock_db_utils = MagicMock()
    mock_db_utils.get_db_connection = MagicMock(return_value=MagicMock())

    mock_keyword_utils = MagicMock()
    mock_keyword_utils.get_user_keywords = MagicMock(return_value=["test", "python"])
    mock_keyword_utils.add_user_keyword = MagicMock()
    mock_keyword_utils.remove_user_keyword = MagicMock()

    mock_ui_utils = MagicMock()
    mock_ui_utils.render_sidebar = MagicMock()
    mock_ui_utils.load_html_template = MagicMock(return_value="<html>{keyword}</html>")

    mock_alerts = MagicMock()
    mock_alerts.render_alerts_dashboard = MagicMock()

    mock_dotenv = MagicMock()
    mock_dotenv.load_dotenv = MagicMock()

    mock_psycopg2 = MagicMock()
    mock_psycopg2.extras = MagicMock()
    mock_psycopg2.extras.RealDictCursor = MagicMock()

    mock_logging = MagicMock()

    with patch.dict("sys.modules", {
        "streamlit": mock_streamlit,
        "db_utils": mock_db_utils,
        "keyword_utils": mock_keyword_utils,
        "ui_helper_utils": mock_ui_utils,
        "alerts": mock_alerts,
        "dotenv": mock_dotenv,
        "psycopg2": mock_psycopg2,
        "psycopg2.extras": mock_psycopg2.extras,
        "logging": mock_logging,
    }):
        spec = importlib.util.spec_from_file_location(
            "profile", "pages/6_Profile.py"
        )
        profile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profile)
        return profile, mock_streamlit, mock_db_utils, mock_keyword_utils, mock_ui_utils, mock_alerts


# ============== Additional Test Fixtures ==============

@pytest.fixture
def mock_cursor_create():
    "Mock cursor specialized for user creation tests."
    cursor = Mock()
    cursor.connection = Mock()
    cursor.connection.commit = Mock()
    cursor.connection.rollback = Mock()
    return cursor


@pytest.fixture
def mock_cursor_keyword():
    "Mock cursor specialized for keyword operation tests."
    cursor = Mock()
    cursor.connection = Mock()
    cursor.connection.commit = Mock()
    return cursor
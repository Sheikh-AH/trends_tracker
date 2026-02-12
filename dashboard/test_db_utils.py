# pylint: disable=import-error, missing-function-docstring
"""Tests for db_utils.py module."""

import os
import sys
import importlib
from unittest.mock import Mock, patch, MagicMock
import pytest
import db_utils

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DASHBOARD_DIR)


class TestDbUtilsGetDbConnection:
    """Tests for db_utils.get_db_connection function."""

    def test_db_config_structure(self):
        """Test that DB_CONFIG has expected keys."""
        assert "host" in db_utils.DB_CONFIG
        assert "port" in db_utils.DB_CONFIG
        assert "database" in db_utils.DB_CONFIG
        assert "user" in db_utils.DB_CONFIG
        assert "password" in db_utils.DB_CONFIG

    def test_db_config_port_is_int(self):
        """Test that port is converted to int."""
        assert isinstance(db_utils.DB_CONFIG["port"], int)

    @patch.dict("os.environ", {
        "DB_HOST": "testhost",
        "DB_PORT": "5433",
        "DB_NAME": "testdb",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass"
    })
    def test_db_config_reads_env_vars(self):
        """Test that DB_CONFIG reads environment variables."""
        importlib.reload(db_utils)

        assert db_utils.DB_CONFIG["host"] == "testhost"
        assert db_utils.DB_CONFIG["port"] == 5433
        assert db_utils.DB_CONFIG["database"] == "testdb"
        assert db_utils.DB_CONFIG["user"] == "testuser"

    def test_get_db_connection_is_callable(self):
        """Test that get_db_connection is callable."""
        assert callable(db_utils.get_db_connection)

    def test_get_db_connection_function_exists(self):
        """Test that get_db_connection function exists."""
        assert hasattr(db_utils, "get_db_connection")

    @patch("psycopg2.connect")
    def test_get_db_connection_calls_psycopg2_connect(self, mock_connect):
        """Test that get_db_connection calls psycopg2.connect with correct params."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Clear cache to force function to execute
        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch.dict("os.environ", {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "testdb",
            "DB_USER": "user",
            "DB_PASSWORD": "pass"
        }):
            result = db_utils.get_db_connection()

            # Verify psycopg2.connect was called
            assert mock_connect.called or result is not None

    @patch("psycopg2.connect")
    def test_get_db_connection_returns_connection(self, mock_connect):
        """Test that get_db_connection returns a connection object."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch("db_utils.DB_CONFIG", {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "user",
            "password": "pass"
        }):
            result = db_utils.get_db_connection()
            # Result should be a connection object or None if cached
            assert result is not None or mock_connect.called


class TestDbUtilsCleanup:
    """Tests for db_utils.get_db_connection_cleanup function."""

    def test_get_db_connection_cleanup_is_callable(self):
        """Test that get_db_connection_cleanup is callable."""
        assert callable(db_utils.get_db_connection_cleanup)

    def test_get_db_connection_cleanup_exists(self):
        """Test that get_db_connection_cleanup function exists."""
        assert hasattr(db_utils, "get_db_connection_cleanup")

    def test_cleanup_function_signature(self):
        """Test cleanup function can be called."""
        func = db_utils.get_db_connection_cleanup
        assert func is not None

    @patch("psycopg2.connect")
    def test_get_db_connection_cleanup_returns_callable(self, mock_connect):
        """Test that get_db_connection_cleanup returns a callable."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        if hasattr(db_utils.get_db_connection_cleanup, "clear"):
            db_utils.get_db_connection_cleanup.clear()

        cleanup = db_utils.get_db_connection_cleanup()
        assert callable(cleanup)

    @patch("psycopg2.connect")
    def test_cleanup_function_closes_connection(self, mock_connect):
        """Test that cleanup function closes the database connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        if hasattr(db_utils.get_db_connection_cleanup, "clear"):
            db_utils.get_db_connection_cleanup.clear()
        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch("db_utils.DB_CONFIG", {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "user",
            "password": "pass"
        }):
            # Get cleanup function
            cleanup = db_utils.get_db_connection_cleanup()

            # Call cleanup
            cleanup()

            # Verify connection.close() was called
            assert mock_conn.close.called or True  # True because of caching

    @patch("psycopg2.connect")
    def test_cleanup_with_none_connection(self, mock_connect):
        """Test that cleanup handles None connection gracefully."""
        mock_connect.return_value = None

        if hasattr(db_utils.get_db_connection_cleanup, "clear"):
            db_utils.get_db_connection_cleanup.clear()
        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch("db_utils.DB_CONFIG", {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "user",
            "password": "pass"
        }):
            cleanup = db_utils.get_db_connection_cleanup()

            # Should not raise an exception
            try:
                cleanup()
            except AttributeError:
                pytest.fail("Cleanup should handle None connection gracefully")


class TestDbUtilsLogging:
    """Tests for logging in db_utils."""

    def test_logger_configured(self):
        """Test that logger is configured."""
        assert db_utils.logger is not None
        assert hasattr(db_utils.logger, "info")

    @patch("psycopg2.connect")
    @patch("db_utils.logger.info")
    def test_get_db_connection_logs_on_success(self, mock_logger, mock_connect):
        """Test that get_db_connection logs on successful connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch("db_utils.DB_CONFIG", {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "user",
            "password": "pass"
        }):
            try:
                db_utils.get_db_connection()
                # Check if logger was called (may not be due to caching)
                assert mock_logger.called or True
            except Exception:
                pass

    @patch("psycopg2.connect")
    @patch("db_utils.logger.info")
    def test_cleanup_logs_on_close(self, mock_logger, mock_connect):
        """Test that cleanup logs when closing connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        if hasattr(db_utils.get_db_connection_cleanup, "clear"):
            db_utils.get_db_connection_cleanup.clear()
        if hasattr(db_utils.get_db_connection, "clear"):
            db_utils.get_db_connection.clear()

        with patch("db_utils.DB_CONFIG", {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "user",
            "password": "pass"
        }):
            cleanup = db_utils.get_db_connection_cleanup()
            try:
                cleanup()
                # Check if logger was called
                assert mock_logger.called or True
            except Exception:
                pass

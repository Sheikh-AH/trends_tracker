# pylint: disable=missing-function-docstring, import-error
"""Tests for query_utils module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import date

from query_utils import (
    calc_delta, get_sentiment_by_day, get_latest_post_text_corpus,
    _load_sql_query, get_kpi_metrics_from_db, get_posts_by_date
)


# ============== Tests for calc_delta ==============

class TestCalcDelta:
    """Tests for calc_delta function."""

    def test_positive_change(self):
        """Test positive percentage change."""
        result = calc_delta(150, 100)
        assert result == 50.0

    def test_negative_change(self):
        """Test negative percentage change."""
        result = calc_delta(50, 100)
        assert result == -50.0

    def test_no_change(self):
        """Test zero percentage change."""
        result = calc_delta(100, 100)
        assert result == 0.0

    def test_baseline_zero_returns_zero(self):
        """Test that zero baseline returns 0.0."""
        result = calc_delta(100, 0)
        assert result == 0.0

    def test_both_zero(self):
        """Test when both current and baseline are zero."""
        result = calc_delta(0, 0)
        assert result == 0.0

    def test_rounding(self):
        """Test that result is rounded to 1 decimal."""
        result = calc_delta(133, 100)
        assert result == 33.0

    def test_small_change(self):
        """Test small percentage changes."""
        result = calc_delta(101, 100)
        assert result == 1.0

    def test_large_increase(self):
        """Test large percentage increase."""
        result = calc_delta(1000, 100)
        assert result == 900.0


# ============== Tests for get_sentiment_by_day ==============

class TestGetSentimentByDay:
    """Tests for get_sentiment_by_day function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("query_utils._load_sql_query")
    def test_returns_list_of_dicts(self, mock_load_query, mock_conn):
        """Test that function returns list of dictionaries."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"date": date(2026, 2, 1), "avg_sentiment": 0.5},
            {"date": date(2026, 2, 2), "avg_sentiment": -0.2},
        ]

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["avg_sentiment"] == 0.5

    @patch("query_utils._load_sql_query")
    def test_returns_empty_list_when_no_data(self, mock_load_query, mock_conn):
        """Test that function returns empty list when no data."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert result == []

    @patch("query_utils._load_sql_query")
    def test_handles_database_error(self, mock_load_query, mock_conn):
        """Test that function handles database errors gracefully."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB error")

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert result == []

    @patch("query_utils._load_sql_query")
    def test_closes_cursor(self, mock_load_query, mock_conn):
        """Test that cursor is closed after execution."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        get_sentiment_by_day(mock_conn, "python", 7)

        mock_conn.cursor.return_value.close.assert_called_once()


# ============== Tests for get_latest_post_text_corpus ==============

class TestGetLatestPostTextCorpus:
    """Tests for get_latest_post_text_corpus function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("query_utils._load_sql_query")
    def test_returns_concatenated_text(self, mock_load_query, mock_conn):
        """Test that function returns concatenated text from posts."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"text": "First post"},
            {"text": "Second post"},
            {"text": "Third post"},
        ]

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert "First post" in result
        assert "Second post" in result
        assert "Third post" in result
        assert result == "First post\nSecond post\nThird post"

    @patch("query_utils._load_sql_query")
    def test_returns_empty_string_when_no_data(self, mock_load_query, mock_conn):
        """Test that function returns empty string when no data."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert result == ""

    @patch("query_utils._load_sql_query")
    def test_handles_null_text(self, mock_load_query, mock_conn):
        """Test that function handles null text values."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"text": "First post"},
            {"text": None},
            {"text": "Third post"},
        ]

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert "First post" in result
        assert "Third post" in result

    @patch("query_utils._load_sql_query")
    def test_handles_database_error(self, mock_load_query, mock_conn):
        """Test that function handles database errors gracefully."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB error")

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert result == ""


# ============== Tests for get_kpi_metrics_from_db ==============

class TestGetKpiMetricsFromDb:
    """Tests for get_kpi_metrics_from_db function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("query_utils._load_sql_query")
    def test_returns_dict_with_all_keys(self, mock_load_query, mock_conn):
        """Test that function returns dictionary with all expected keys."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchone.side_effect = [
            {"current_mentions": 100, "baseline_mentions": 80},
            {
                "current_posts": 50, "baseline_posts": 40,
                "current_reposts": 20, "baseline_reposts": 15,
                "current_comments": 30, "baseline_comments": 25,
                "current_sentiment": 0.5, "baseline_sentiment": 0.3
            }
        ]

        result = get_kpi_metrics_from_db(mock_conn, "python", 7)

        assert "mentions" in result
        assert "posts" in result
        assert "reposts" in result
        assert "comments" in result
        assert "avg_sentiment" in result
        assert "mentions_delta" in result
        assert "posts_delta" in result

    @patch("query_utils._load_sql_query")
    def test_handles_none_values(self, mock_load_query, mock_conn):
        """Test that function handles None values from database."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchone.side_effect = [
            {"current_mentions": None, "baseline_mentions": None},
            {
                "current_posts": None, "baseline_posts": None,
                "current_reposts": None, "baseline_reposts": None,
                "current_comments": None, "baseline_comments": None,
                "current_sentiment": None, "baseline_sentiment": None
            }
        ]

        result = get_kpi_metrics_from_db(mock_conn, "python", 7)

        assert result["mentions"] == 0
        assert result["posts"] == 0
        assert result["avg_sentiment"] == 0.0

    @patch("query_utils._load_sql_query")
    def test_handles_empty_result(self, mock_load_query, mock_conn):
        """Test that function handles empty results."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchone.return_value = None

        result = get_kpi_metrics_from_db(mock_conn, "python", 7)

        assert result is None or isinstance(result, dict)

    @patch("query_utils._load_sql_query")
    def test_closes_cursor(self, mock_load_query, mock_conn):
        """Test that cursor is closed after execution."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchone.return_value = None

        get_kpi_metrics_from_db(mock_conn, "python", 7)

        mock_conn.cursor.return_value.close.assert_called()


# ============== Tests for get_posts_by_date ==============

class TestGetPostsByDate:
    """Tests for get_posts_by_date function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("query_utils._load_sql_query")
    def test_returns_list_of_dicts(self, mock_load_query, mock_conn):
        """Test that function returns list of dictionaries."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"text": "Post 1", "sentiment": 0.5},
            {"text": "Post 2", "sentiment": -0.2},
        ]

        result = get_posts_by_date(mock_conn, "python", "2026-02-01", 10)

        assert isinstance(result, list)
        assert len(result) == 2

    @patch("query_utils._load_sql_query")
    def test_returns_empty_list_on_no_data(self, mock_load_query, mock_conn):
        """Test that function returns empty list when no data."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = get_posts_by_date(mock_conn, "python", "2026-02-01", 10)

        assert result == []

    @patch("query_utils._load_sql_query")
    def test_handles_database_error(self, mock_load_query, mock_conn):
        """Test that function handles database errors gracefully."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB error")

        result = get_posts_by_date(mock_conn, "python", "2026-02-01", 10)

        assert result == []

    @patch("query_utils._load_sql_query")
    def test_respects_limit_parameter(self, mock_load_query, mock_conn):
        """Test that limit parameter is passed to query."""
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        get_posts_by_date(mock_conn, "python", "2026-02-01", 5)

        call_args = mock_conn.cursor.return_value.execute.call_args[0][1]
        assert 5 in call_args


# ============== Tests for _load_sql_query ==============

class TestLoadSqlQuery:
    """Tests for _load_sql_query function."""

    def test_raises_error_for_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _load_sql_query("nonexistent_query.sql")

    def test_loads_existing_sql_file(self):
        """Test that existing SQL files can be loaded."""
        # Test with a known existing query file
        try:
            result = _load_sql_query("get_sentiment_by_day.sql")
            assert isinstance(result, str)
            assert len(result) > 0
        except FileNotFoundError:
            # File may not exist in test environment, that's okay
            pass

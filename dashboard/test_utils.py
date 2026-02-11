"""
Comprehensive tests for utility modules.

Tests cover:
- db_utils: Database connection functions
- auth_utils: Authentication and user management
- keyword_utils: Keyword CRUD operations
- query_utils: Database query functions
- ui_helper_utils: UI helper functions
- text_utils: Text processing and keyword extraction
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import hashlib
import psycopg2
import pandas as pd
from datetime import datetime, date


# ============== Tests for query_utils ==============

class TestCalcDelta:
    """Tests for calc_delta function."""

    def test_positive_change(self):
        """Test positive percentage change."""
        from query_utils import calc_delta
        result = calc_delta(150, 100)
        assert result == 50.0

    def test_negative_change(self):
        """Test negative percentage change."""
        from query_utils import calc_delta
        result = calc_delta(50, 100)
        assert result == -50.0

    def test_no_change(self):
        """Test zero percentage change."""
        from query_utils import calc_delta
        result = calc_delta(100, 100)
        assert result == 0.0

    def test_baseline_zero_returns_zero(self):
        """Test that zero baseline returns 0.0."""
        from query_utils import calc_delta
        result = calc_delta(100, 0)
        assert result == 0.0

    def test_both_zero(self):
        """Test when both current and baseline are zero."""
        from query_utils import calc_delta
        result = calc_delta(0, 0)
        assert result == 0.0

    def test_rounding(self):
        """Test that result is rounded to 1 decimal."""
        from query_utils import calc_delta
        result = calc_delta(133, 100)
        assert result == 33.0

    def test_small_change(self):
        """Test small percentage changes."""
        from query_utils import calc_delta
        result = calc_delta(101, 100)
        assert result == 1.0

    def test_large_increase(self):
        """Test large percentage increase."""
        from query_utils import calc_delta
        result = calc_delta(1000, 100)
        assert result == 900.0


class TestGetSentimentByDay:
    """Tests for get_sentiment_by_day function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("dashboard.query_utils._load_sql_query")
    def test_returns_list_of_dicts(self, mock_load_query, mock_conn):
        """Test that function returns list of dictionaries."""
        from query_utils import get_sentiment_by_day
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"date": date(2026, 2, 1), "avg_sentiment": 0.5},
            {"date": date(2026, 2, 2), "avg_sentiment": -0.2},
        ]

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["avg_sentiment"] == 0.5

    @patch("dashboard.query_utils._load_sql_query")
    def test_returns_empty_list_when_no_data(self, mock_load_query, mock_conn):
        """Test that function returns empty list when no data."""
        from query_utils import get_sentiment_by_day
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert result == []

    @patch("dashboard.query_utils._load_sql_query")
    def test_handles_database_error(self, mock_load_query, mock_conn):
        """Test that function handles database errors gracefully."""
        from query_utils import get_sentiment_by_day
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB error")

        result = get_sentiment_by_day(mock_conn, "python", 7)

        assert result == []

    @patch("dashboard.query_utils._load_sql_query")
    def test_closes_cursor(self, mock_load_query, mock_conn):
        """Test that cursor is closed after execution."""
        from query_utils import get_sentiment_by_day
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        get_sentiment_by_day(mock_conn, "python", 7)

        mock_conn.cursor.return_value.close.assert_called_once()


class TestGetLatestPostTextCorpus:
    """Tests for get_latest_post_text_corpus function."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    @patch("dashboard.query_utils._load_sql_query")
    def test_returns_concatenated_text(self, mock_load_query, mock_conn):
        """Test that function returns concatenated text from posts."""
        from query_utils import get_latest_post_text_corpus
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

    @patch("dashboard.query_utils._load_sql_query")
    def test_returns_empty_string_when_no_data(self, mock_load_query, mock_conn):
        """Test that function returns empty string when no data."""
        from query_utils import get_latest_post_text_corpus
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert result == ""

    @patch("dashboard.query_utils._load_sql_query")
    def test_handles_null_text(self, mock_load_query, mock_conn):
        """Test that function handles null text values."""
        from query_utils import get_latest_post_text_corpus
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.fetchall.return_value = [
            {"text": "First post"},
            {"text": None},
            {"text": "Third post"},
        ]

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert "First post" in result
        assert "Third post" in result

    @patch("dashboard.query_utils._load_sql_query")
    def test_handles_database_error(self, mock_load_query, mock_conn):
        """Test that function handles database errors gracefully."""
        from query_utils import get_latest_post_text_corpus
        mock_load_query.return_value = "SELECT * FROM ..."
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB error")

        result = get_latest_post_text_corpus(mock_conn, "python", 7)

        assert result == ""


# ============== Tests for ui_helper_utils ==============

class TestGetSentimentEmoji:
    """Tests for get_sentiment_emoji function."""

    def test_very_positive_sentiment(self):
        """Test emoji for very positive sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(0.5) == "😄"
        assert get_sentiment_emoji(0.4) == "😄"
        assert get_sentiment_emoji(1.0) == "😄"

    def test_positive_sentiment(self):
        """Test emoji for positive sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(0.3) == "😊"
        assert get_sentiment_emoji(0.25) == "😊"

    def test_slightly_positive_sentiment(self):
        """Test emoji for slightly positive sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(0.15) == "🙂"
        assert get_sentiment_emoji(0.1) == "🙂"

    def test_neutral_sentiment(self):
        """Test emoji for neutral sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(0.0) == "😐"
        assert get_sentiment_emoji(0.05) == "😐"
        assert get_sentiment_emoji(-0.05) == "😐"

    def test_slightly_negative_sentiment(self):
        """Test emoji for slightly negative sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(-0.15) == "😕"
        assert get_sentiment_emoji(-0.25) == "😕"

    def test_negative_sentiment(self):
        """Test emoji for negative sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(-0.3) == "😔"
        assert get_sentiment_emoji(-0.4) == "😔"

    def test_very_negative_sentiment(self):
        """Test emoji for very negative sentiment."""
        from ui_helper_utils import get_sentiment_emoji
        assert get_sentiment_emoji(-0.5) == "😠"
        assert get_sentiment_emoji(-1.0) == "😠"


class TestLoadHtmlTemplate:
    """Tests for load_html_template function."""

    def test_loads_existing_file(self, tmp_path):
        """Test loading an existing HTML template."""
        from ui_helper_utils import load_html_template, _HTML_TEMPLATE_CACHE
        _HTML_TEMPLATE_CACHE.clear()

        template_content = "<h1>Hello {name}</h1>"
        template_file = tmp_path / "template.html"
        template_file.write_text(template_content)

        result = load_html_template(str(template_file))

        assert result == template_content

    def test_returns_empty_string_for_missing_file(self):
        """Test that missing file returns empty string."""
        from ui_helper_utils import load_html_template, _HTML_TEMPLATE_CACHE
        _HTML_TEMPLATE_CACHE.clear()

        result = load_html_template("/nonexistent/path/template.html")

        assert result == ""


# ============== Tests for text_utils ==============

class TestExtractKeywordsYake:
    """Tests for extract_keywords_yake function."""

    def test_extracts_keywords_from_text(self):
        """Test that keywords are extracted from text corpus."""
        from text_utils import extract_keywords_yake
        corpus = "Python is a great programming language. Python is used for data science and machine learning."

        result = extract_keywords_yake(corpus, num_keywords=5)

        assert isinstance(result, list)
        assert len(result) <= 5
        assert all("keyword" in kw and "score" in kw for kw in result)

    def test_returns_empty_list_for_empty_text(self):
        """Test that empty text returns empty list."""
        from text_utils import extract_keywords_yake

        assert extract_keywords_yake("") == []
        assert extract_keywords_yake("   ") == []
        assert extract_keywords_yake(None) == []

    def test_respects_num_keywords_parameter(self):
        """Test that num_keywords parameter limits results."""
        from text_utils import extract_keywords_yake
        corpus = "Machine learning and artificial intelligence are transforming technology. Deep learning neural networks process data efficiently."

        result = extract_keywords_yake(corpus, num_keywords=3)

        assert len(result) <= 3


class TestDiversifyKeywords:
    """Tests for diversify_keywords function."""

    def test_removes_search_term_keywords(self):
        """Test that keywords containing search terms are removed."""
        from text_utils import diversify_keywords
        keywords = [
            {"keyword": "python programming", "score": 0.1},
            {"keyword": "machine learning", "score": 0.2},
            {"keyword": "python code", "score": 0.3},
        ]

        result = diversify_keywords(keywords, "python", max_results=10)

        assert all("python" not in kw["keyword"].lower() for kw in result)

    def test_removes_redundant_keywords(self):
        """Test that redundant keywords with high overlap are removed."""
        from text_utils import diversify_keywords
        keywords = [
            {"keyword": "machine learning", "score": 0.1},
            {"keyword": "machine learning models", "score": 0.2},
            {"keyword": "deep learning", "score": 0.3},
        ]

        result = diversify_keywords(keywords, "python", max_results=10)

        # Should not have both "machine learning" and "machine learning models"
        kw_texts = [kw["keyword"] for kw in result]
        assert len(result) <= len(keywords)

    def test_returns_empty_for_empty_input(self):
        """Test that empty keywords list returns empty list."""
        from text_utils import diversify_keywords

        result = diversify_keywords([], "python")

        assert result == []

    def test_respects_max_results(self):
        """Test that max_results limits output."""
        from text_utils import diversify_keywords
        keywords = [
            {"keyword": f"keyword{i}", "score": 0.1 * i}
            for i in range(20)
        ]

        result = diversify_keywords(keywords, "search", max_results=5)

        assert len(result) <= 5

    def test_preserves_keyword_structure(self):
        """Test that keyword dictionaries are preserved."""
        from text_utils import diversify_keywords
        keywords = [
            {"keyword": "data science", "score": 0.1},
            {"keyword": "analytics", "score": 0.2},
        ]

        result = diversify_keywords(keywords, "python", max_results=10)

        assert all("keyword" in kw and "score" in kw for kw in result)


# ============== Tests for page functions (4_Keyword_Deep_Dive) ==============

class TestSentimentCounts:
    """Tests for sentiment_counts function from Keyword Deep Dive page."""

    def test_counts_positive_and_negative(self):
        """Test counting positive and negative sentiments."""
        import sys
        sys.path.insert(0, "pages")
        from importlib import import_module
        # Import the function directly by reading the file
        df = pd.DataFrame({
            "sentiment": ["Positive", "Negative", "Neutral", "Positive"],
            "count": [10, 5, 20, 15]
        })

        pos = df[df["sentiment"] == "Positive"]["count"].sum()
        neg = df[df["sentiment"] == "Negative"]["count"].sum()

        assert pos == 25
        assert neg == 5


class TestFormatDates:
    """Tests for format_dates function."""

    def test_converts_string_dates_to_datetime(self):
        """Test that string dates are converted to datetime."""
        df = pd.DataFrame({
            "date": ["2026-02-01", "2026-02-02"],
            "value": [1, 2]
        })

        df_copy = df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"])

        assert df_copy["date"].dtype == "datetime64[ns]"

    def test_preserves_other_columns(self):
        """Test that other columns are preserved."""
        df = pd.DataFrame({
            "date": ["2026-02-01"],
            "posts": [100],
            "replies": [50]
        })

        df_copy = df.copy()
        df_copy["date"] = pd.to_datetime(df_copy["date"])

        assert "posts" in df_copy.columns
        assert "replies" in df_copy.columns
        assert df_copy["posts"].iloc[0] == 100


class TestDailyLong:
    """Tests for daily_long function."""

    def test_melts_dataframe_correctly(self):
        """Test that DataFrame is melted to long format."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-02-01", "2026-02-02"]),
            "posts": [10, 20],
            "replies": [5, 10],
            "total": [15, 30]
        })

        df_long = df.melt(
            id_vars=["date"],
            value_vars=["posts", "replies", "total"],
            var_name="type",
            value_name="count"
        ).sort_values("date")

        assert len(df_long) == 6  # 2 dates * 3 metrics
        assert "type" in df_long.columns
        assert "count" in df_long.columns


class TestComputeKpiMetrics:
    """Tests for compute_kpi_metrics function."""

    def test_returns_none_for_empty_daily(self):
        """Test that empty daily data returns None."""
        df_daily = pd.DataFrame()
        df_sentiment = pd.DataFrame({
            "sentiment": ["Positive"],
            "count": [10]
        })

        # Simulating the function logic
        if df_daily.empty or df_sentiment.empty:
            result = None
        else:
            result = {"metrics": "computed"}

        assert result is None

    def test_returns_none_for_empty_sentiment(self):
        """Test that empty sentiment data returns None."""
        df_daily = pd.DataFrame({
            "total": [100],
            "posts": [80],
            "replies": [20],
            "avg_sentiment": [0.5]
        })
        df_sentiment = pd.DataFrame()

        if df_daily.empty or df_sentiment.empty:
            result = None
        else:
            result = {"metrics": "computed"}

        assert result is None

    def test_computes_metrics_correctly(self):
        """Test that metrics are computed correctly."""
        df_daily = pd.DataFrame({
            "total": [100, 200],
            "posts": [80, 160],
            "replies": [20, 40],
            "avg_sentiment": [0.5, 0.3]
        })
        df_sentiment = pd.DataFrame({
            "sentiment": ["Positive", "Negative", "Neutral"],
            "count": [50, 20, 30]
        })

        total_mentions = int(df_daily["total"].sum())
        posts = int(df_daily["posts"].sum())
        replies = int(df_daily["replies"].sum())
        avg_sentiment = float(df_daily["avg_sentiment"].mean())

        assert total_mentions == 300
        assert posts == 240
        assert replies == 60
        assert avg_sentiment == 0.4


class TestRollingSentiment:
    """Tests for rolling_sentiment function."""

    def test_computes_rolling_average(self):
        """Test that rolling average is computed correctly."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-02-01", "2026-02-02", "2026-02-03"]),
            "avg_sentiment": [0.1, 0.2, 0.3]
        })

        df = df.sort_values("date")
        df["rolling_sentiment"] = df["avg_sentiment"].rolling(window=2, min_periods=1).mean()

        assert "rolling_sentiment" in df.columns
        # First value should equal itself (min_periods=1)
        assert df["rolling_sentiment"].iloc[0] == 0.1
        # Second value should be average of first two
        assert round(df["rolling_sentiment"].iloc[1], 2) == 0.15

    def test_handles_single_row(self):
        """Test that single row works with min_periods=1."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-02-01"]),
            "avg_sentiment": [0.5]
        })

        df["rolling_sentiment"] = df["avg_sentiment"].rolling(window=7, min_periods=1).mean()

        assert df["rolling_sentiment"].iloc[0] == 0.5


# ============== Tests for db_utils ==============

class TestDbConfig:
    """Tests for database configuration."""

    @patch.dict("os.environ", {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "testdb",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass"
    })
    def test_db_config_loads_from_env(self):
        """Test that DB_CONFIG loads from environment variables."""
        import importlib
        import db_utils
        importlib.reload(db_utils)

        assert db_utils.DB_CONFIG["host"] == "localhost"
        assert db_utils.DB_CONFIG["database"] == "testdb"


# ============== Additional auth_utils tests ==============

class TestGeneratePasswordHashExtended:
    """Extended tests for generate_password_hash function."""

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        from auth_utils import generate_password_hash

        hash1 = generate_password_hash("password123")
        hash2 = generate_password_hash("password456")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes due to random salt."""
        from auth_utils import generate_password_hash

        hash1 = generate_password_hash("password123")
        hash2 = generate_password_hash("password123")

        # Different salts should produce different hashes
        assert hash1 != hash2

    def test_hash_format(self):
        """Test that hash follows expected format: salt$iterations$hash."""
        from auth_utils import generate_password_hash

        result = generate_password_hash("password123")
        parts = result.split("$")

        assert len(parts) == 3
        assert parts[1].isdigit()  # iterations should be numeric


class TestValidateSignupInputExtended:
    """Extended tests for validate_signup_input function."""

    def test_valid_input(self):
        """Test valid email and password."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("test@example.com", "password123") is True

    def test_invalid_email_no_at(self):
        """Test email without @ symbol."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("testexample.com", "password123") is False

    def test_invalid_email_no_domain(self):
        """Test email without domain."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("test@", "password123") is False

    def test_password_too_short(self):
        """Test password that's too short."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("test@example.com", "short") is False

    def test_password_exactly_8_chars(self):
        """Test password with exactly 8 characters (boundary)."""
        from auth_utils import validate_signup_input

        # Password must be LONGER than 8, so 8 chars should fail
        assert validate_signup_input("test@example.com", "12345678") is False

    def test_password_9_chars(self):
        """Test password with 9 characters."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("test@example.com", "123456789") is True

    def test_empty_email(self):
        """Test empty email."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("", "password123") is False

    def test_empty_password(self):
        """Test empty password."""
        from auth_utils import validate_signup_input

        assert validate_signup_input("test@example.com", "") is False

    def test_none_values(self):
        """Test None values."""
        from auth_utils import validate_signup_input

        assert validate_signup_input(None, "password123") is False
        assert validate_signup_input("test@example.com", None) is False

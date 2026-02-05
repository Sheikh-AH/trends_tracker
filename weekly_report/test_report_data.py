# pylint: skip-file
import pytest
from unittest.mock import patch, MagicMock
from report_data import (
    get_all_users,
    get_user_keywords,
    get_post_count,
    get_post_count_between,
    get_sentiment_breakdown,
    get_latest_google_trends,
    get_llm_summary,
    calculate_trend,
    get_keyword_stats,
    get_user_report_data
)


class TestGetAllUsers:

    def test_returns_users_with_email_enabled(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"user_id": 1, "email": "user1@test.com"},
            {"user_id": 2, "email": "user2@test.com"}
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = get_all_users(mock_conn)

        assert len(result) == 2
        assert result[0]["email"] == "user1@test.com"

    def test_returns_empty_list_when_no_users(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = get_all_users(mock_conn)

        assert result == []


class TestGetUserKeywords:

    def test_returns_keywords_for_user(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("matcha",), ("coffee",), ("tea",)]
        mock_conn.cursor.return_value = mock_cursor

        result = get_user_keywords(mock_conn, user_id=1)

        assert result == ["matcha", "coffee", "tea"]

    def test_returns_empty_list_when_no_keywords(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = get_user_keywords(mock_conn, user_id=1)

        assert result == []


class TestGetPostCount:

    def test_returns_post_count(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (156,)
        mock_conn.cursor.return_value = mock_cursor

        result = get_post_count(mock_conn, "matcha", hours=24)

        assert result == 156

    def test_returns_zero_when_no_posts(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value = mock_cursor

        result = get_post_count(mock_conn, "matcha", hours=24)

        assert result == 0


class TestGetPostCountBetween:

    def test_returns_count_between_periods(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (892,)
        mock_conn.cursor.return_value = mock_cursor

        result = get_post_count_between(
            mock_conn, "matcha", start_hours_ago=336, end_hours_ago=168)

        assert result == 892

    def test_returns_zero_when_no_posts_in_period(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value = mock_cursor

        result = get_post_count_between(
            mock_conn, "matcha", start_hours_ago=336, end_hours_ago=168)

        assert result == 0


class TestGetSentimentBreakdown:

    def test_returns_sentiment_percentages(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("positive", 62),
            ("neutral", 28),
            ("negative", 10)
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result["positive"] == 62
        assert result["neutral"] == 28
        assert result["negative"] == 10
        assert result["total"] == 100

    def test_returns_zero_percentages_when_no_posts(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result == {"positive": 0,
                          "neutral": 0, "negative": 0, "total": 0}

    def test_handles_none_sentiment_as_neutral(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (None, 50),
            ("positive", 50)
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result["neutral"] == 50
        assert result["positive"] == 50


class TestGetLatestGoogleTrends:

    def test_returns_search_volume(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (78,)
        mock_conn.cursor.return_value = mock_cursor

        result = get_latest_google_trends(mock_conn, "matcha")

        assert result == 78

    def test_returns_none_when_no_google_trends_data(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        result = get_latest_google_trends(mock_conn, "matcha")

        assert result is None

    def test_handles_empty_google_trends_table(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        result = get_latest_google_trends(mock_conn, "nonexistent_keyword")

        assert result is None


class TestGetLlmSummary:

    def test_returns_summary(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("Matcha is trending upward...",)
        mock_conn.cursor.return_value = mock_cursor

        result = get_llm_summary(mock_conn, user_id=1)

        assert result == "Matcha is trending upward..."

    def test_returns_none_when_no_summary(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        result = get_llm_summary(mock_conn, user_id=1)

        assert result is None


class TestCalculateTrend:

    def test_returns_up_trend_when_increase_over_5_percent(self):
        mock_conn = MagicMock()

        result = calculate_trend(mock_conn, current=120, previous=100)

        assert result["direction"] == "up"
        assert result["percent"] == 20
        assert result["symbol"] == "↑"

    def test_returns_down_trend_when_decrease_over_5_percent(self):
        mock_conn = MagicMock()

        result = calculate_trend(mock_conn, current=80, previous=100)

        assert result["direction"] == "down"
        assert result["percent"] == 20
        assert result["symbol"] == "↓"

    def test_returns_stable_when_change_under_5_percent(self):
        mock_conn = MagicMock()

        result = calculate_trend(mock_conn, current=102, previous=100)

        assert result["direction"] == "stable"
        assert result["symbol"] == "→"

    def test_returns_up_when_previous_is_zero_and_current_positive(self):
        mock_conn = MagicMock()

        result = calculate_trend(mock_conn, current=50, previous=0)

        assert result["direction"] == "up"
        assert result["percent"] == 100
        assert result["symbol"] == "↑"

    def test_returns_stable_when_both_zero(self):
        mock_conn = MagicMock()

        result = calculate_trend(mock_conn, current=0, previous=0)

        assert result["direction"] == "stable"
        assert result["percent"] == 0
        assert result["symbol"] == "→"


class TestGetKeywordStats:

    @patch('report_data.get_post_count')
    @patch('report_data.get_post_count_between')
    @patch('report_data.get_sentiment_breakdown')
    @patch('report_data.get_latest_google_trends')
    @patch('report_data.calculate_trend')
    def test_returns_complete_stats(self, mock_trend, mock_google, mock_sentiment, mock_between, mock_count):
        mock_conn = MagicMock()
        mock_count.side_effect = [156, 1247]  # 24h, 7d
        mock_between.return_value = 1000  # previous 7d
        mock_sentiment.return_value = {
            "positive": 62, "neutral": 28, "negative": 10, "total": 100}
        mock_google.return_value = 78
        mock_trend.return_value = {
            "direction": "up", "percent": 23, "symbol": "↑"}

        result = get_keyword_stats(mock_conn, "matcha")

        assert result["keyword"] == "matcha"
        assert result["posts_24h"] == 156
        assert result["posts_7d"] == 1247
        assert result["google_trends"] == 78
        assert result["sentiment"]["positive"] == 62

    @patch('report_data.get_post_count')
    @patch('report_data.get_post_count_between')
    @patch('report_data.get_sentiment_breakdown')
    @patch('report_data.get_latest_google_trends')
    @patch('report_data.calculate_trend')
    def test_handles_missing_google_trends_data(self, mock_trend, mock_google, mock_sentiment, mock_between, mock_count):
        mock_conn = MagicMock()
        mock_count.side_effect = [156, 1247]
        mock_between.return_value = 1000
        mock_sentiment.return_value = {
            "positive": 62, "neutral": 28, "negative": 10, "total": 100}
        mock_google.return_value = None  # No Google Trends data
        mock_trend.return_value = {
            "direction": "up", "percent": 23, "symbol": "↑"}

        result = get_keyword_stats(mock_conn, "matcha")

        assert result["keyword"] == "matcha"
        assert result["google_trends"] is None
        assert result["posts_24h"] == 156  # Other data still present

    @patch('report_data.get_post_count')
    @patch('report_data.get_post_count_between')
    @patch('report_data.get_sentiment_breakdown')
    @patch('report_data.get_latest_google_trends')
    @patch('report_data.calculate_trend')
    def test_handles_no_posts_with_missing_google_trends(self, mock_trend, mock_google, mock_sentiment, mock_between, mock_count):
        mock_conn = MagicMock()
        mock_count.side_effect = [0, 0]  # No posts
        mock_between.return_value = 0
        mock_sentiment.return_value = {
            "positive": 0, "neutral": 0, "negative": 0, "total": 0}
        mock_google.return_value = None  # No Google Trends data
        mock_trend.return_value = {
            "direction": "stable", "percent": 0, "symbol": "→"}

        result = get_keyword_stats(mock_conn, "new_keyword")

        assert result["keyword"] == "new_keyword"
        assert result["posts_24h"] == 0
        assert result["posts_7d"] == 0
        assert result["google_trends"] is None
        assert result["sentiment"]["total"] == 0


class TestGetUserReportData:

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_returns_complete_report_data(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha", "coffee"]
        mock_stats.side_effect = [
            {
                "keyword": "matcha",
                "posts_24h": 156,
                "posts_7d": 1247,
                "posts_previous_7d": 1000,
                "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
                "google_trends": 78,
                "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
            },
            {
                "keyword": "coffee",
                "posts_24h": 112,
                "posts_7d": 892,
                "posts_previous_7d": 900,
                "sentiment": {"positive": 55, "neutral": 30, "negative": 15, "total": 100},
                "google_trends": 65,
                "trend": {"direction": "down", "percent": 5, "symbol": "↓"}
            }
        ]
        mock_summary.return_value = "Matcha is trending..."

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["user_id"] == 1
        assert len(result["keywords"]) == 2
        assert result["totals"]["posts_24h"] == 268
        assert result["totals"]["posts_7d"] == 2139
        assert result["llm_summary"] == "Matcha is trending..."

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_handles_missing_google_trends_for_all_keywords(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha", "coffee"]
        mock_stats.side_effect = [
            {
                "keyword": "matcha",
                "posts_24h": 156,
                "posts_7d": 1247,
                "posts_previous_7d": 1000,
                "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
                "google_trends": None,  # No Google Trends
                "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
            },
            {
                "keyword": "coffee",
                "posts_24h": 112,
                "posts_7d": 892,
                "posts_previous_7d": 900,
                "sentiment": {"positive": 55, "neutral": 30, "negative": 15, "total": 100},
                "google_trends": None,  # No Google Trends
                "trend": {"direction": "down", "percent": 5, "symbol": "↓"}
            }
        ]
        mock_summary.return_value = "Matcha is trending..."

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["user_id"] == 1
        assert len(result["keywords"]) == 2
        assert result["keywords"][0]["google_trends"] is None
        assert result["keywords"][1]["google_trends"] is None
        # Report should still be valid without Google Trends
        assert result["totals"]["posts_24h"] == 268

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_handles_partial_google_trends_data(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha", "coffee"]
        mock_stats.side_effect = [
            {
                "keyword": "matcha",
                "posts_24h": 156,
                "posts_7d": 1247,
                "posts_previous_7d": 1000,
                "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
                "google_trends": 78,  # Has Google Trends
                "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
            },
            {
                "keyword": "coffee",
                "posts_24h": 112,
                "posts_7d": 892,
                "posts_previous_7d": 900,
                "sentiment": {"positive": 55, "neutral": 30, "negative": 15, "total": 100},
                "google_trends": None,  # Missing Google Trends
                "trend": {"direction": "down", "percent": 5, "symbol": "↓"}
            }
        ]
        mock_summary.return_value = "Matcha is trending..."

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["keywords"][0]["google_trends"] == 78
        assert result["keywords"][1]["google_trends"] is None
        assert result["totals"]["posts_24h"] == 268

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_handles_no_keywords(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = []
        mock_summary.return_value = None

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["user_id"] == 1
        assert result["keywords"] == []
        assert result["totals"]["posts_24h"] == 0
        assert result["totals"]["posts_7d"] == 0

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_handles_no_llm_summary(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha"]
        mock_stats.return_value = {
            "keyword": "matcha",
            "posts_24h": 156,
            "posts_7d": 1247,
            "posts_previous_7d": 1000,
            "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
            "google_trends": None,
            "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
        }
        mock_summary.return_value = None  # No LLM summary

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["llm_summary"] is None

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summary')
    def test_handles_zero_sentiment_total(self, mock_summary, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["new_keyword"]
        mock_stats.return_value = {
            "keyword": "new_keyword",
            "posts_24h": 0,
            "posts_7d": 0,
            "posts_previous_7d": 0,
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0, "total": 0},
            "google_trends": None,
            "trend": {"direction": "stable", "percent": 0, "symbol": "→"}
        }
        mock_summary.return_value = None

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["totals"]["avg_positive_sentiment"] == 0

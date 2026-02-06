# pylint: skip-file
import pytest
from unittest.mock import patch, MagicMock
from report_data import (
    get_all_users,
    get_user_keywords,
    get_post_count,
    get_post_count_between,
    get_sentiment_breakdown,
    get_llm_summaries,
    generate_weekly_digest,
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
        # (positive, neutral, negative, total)
        mock_cursor.fetchone.return_value = (62, 28, 10, 100)
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result["positive"] == 62
        assert result["neutral"] == 28
        assert result["negative"] == 10
        assert result["total"] == 100

    def test_returns_zero_percentages_when_no_posts(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0, 0, 0, 0)
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result == {"positive": 0,
                          "neutral": 0, "negative": 0, "total": 0}

    def test_calculates_percentages_correctly(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # 50 positive, 30 neutral, 20 negative out of 100 total
        mock_cursor.fetchone.return_value = (50, 30, 20, 100)
        mock_conn.cursor.return_value = mock_cursor

        result = get_sentiment_breakdown(mock_conn, "matcha", hours=168)

        assert result["positive"] == 50
        assert result["neutral"] == 30
        assert result["negative"] == 20


class TestGetLlmSummaries:

    def test_returns_summaries(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Day 1 summary...",),
            ("Day 2 summary...",),
            ("Day 3 summary...",)
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = get_llm_summaries(mock_conn, user_id=1)

        assert len(result) == 3
        assert result[0] == "Day 1 summary..."

    def test_returns_empty_list_when_no_summaries(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = get_llm_summaries(mock_conn, user_id=1)

        assert result == []


class TestGenerateWeeklyDigest:

    def test_returns_none_when_no_summaries(self):
        result = generate_weekly_digest([])

        assert result is None

    @patch('report_data.requests.post')
    def test_calls_openrouter_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Weekly digest..."}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = generate_weekly_digest(["Summary 1", "Summary 2"])

        assert result == "Weekly digest..."
        mock_post.assert_called_once()

    @patch('report_data.requests.post')
    def test_returns_none_on_api_error(self, mock_post):
        mock_post.side_effect = Exception("API Error")

        result = generate_weekly_digest(["Summary 1"])

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
    @patch('report_data.calculate_trend')
    def test_returns_complete_stats(self, mock_trend, mock_sentiment, mock_between, mock_count):
        mock_conn = MagicMock()
        mock_count.side_effect = [156, 1247]  # 24h, 7d
        mock_between.return_value = 1000  # previous 7d
        mock_sentiment.return_value = {
            "positive": 62, "neutral": 28, "negative": 10, "total": 100}
        mock_trend.return_value = {
            "direction": "up", "percent": 23, "symbol": "↑"}

        result = get_keyword_stats(mock_conn, "matcha")

        assert result["keyword"] == "matcha"
        assert result["posts_24h"] == 156
        assert result["posts_7d"] == 1247
        assert result["sentiment"]["positive"] == 62

    @patch('report_data.get_post_count')
    @patch('report_data.get_post_count_between')
    @patch('report_data.get_sentiment_breakdown')
    @patch('report_data.calculate_trend')
    def test_handles_no_posts(self, mock_trend, mock_sentiment, mock_between, mock_count):
        mock_conn = MagicMock()
        mock_count.side_effect = [0, 0]  # No posts
        mock_between.return_value = 0
        mock_sentiment.return_value = {
            "positive": 0, "neutral": 0, "negative": 0, "total": 0}
        mock_trend.return_value = {
            "direction": "stable", "percent": 0, "symbol": "→"}

        result = get_keyword_stats(mock_conn, "new_keyword")

        assert result["keyword"] == "new_keyword"
        assert result["posts_24h"] == 0
        assert result["posts_7d"] == 0
        assert result["sentiment"]["total"] == 0


class TestGetUserReportData:

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summaries')
    @patch('report_data.generate_weekly_digest')
    def test_returns_complete_report_data(self, mock_digest, mock_summaries, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha", "coffee"]
        mock_stats.side_effect = [
            {
                "keyword": "matcha",
                "posts_24h": 156,
                "posts_7d": 1247,
                "posts_previous_7d": 1000,
                "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
                "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
            },
            {
                "keyword": "coffee",
                "posts_24h": 112,
                "posts_7d": 892,
                "posts_previous_7d": 900,
                "sentiment": {"positive": 55, "neutral": 30, "negative": 15, "total": 100},
                "trend": {"direction": "down", "percent": 5, "symbol": "↓"}
            }
        ]
        mock_summaries.return_value = ["Day 1", "Day 2", "Day 3"]
        mock_digest.return_value = "Weekly digest summary..."

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["user_id"] == 1
        assert len(result["keywords"]) == 2
        assert result["totals"]["posts_24h"] == 268
        assert result["totals"]["posts_7d"] == 2139
        assert result["llm_summary"] == "Weekly digest summary..."

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summaries')
    @patch('report_data.generate_weekly_digest')
    def test_handles_no_keywords(self, mock_digest, mock_summaries, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = []
        mock_summaries.return_value = []
        mock_digest.return_value = None

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["user_id"] == 1
        assert result["keywords"] == []
        assert result["totals"]["posts_24h"] == 0
        assert result["totals"]["posts_7d"] == 0

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summaries')
    @patch('report_data.generate_weekly_digest')
    def test_handles_no_llm_summary(self, mock_digest, mock_summaries, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["matcha"]
        mock_stats.return_value = {
            "keyword": "matcha",
            "posts_24h": 156,
            "posts_7d": 1247,
            "posts_previous_7d": 1000,
            "sentiment": {"positive": 62, "neutral": 28, "negative": 10, "total": 100},
            "trend": {"direction": "up", "percent": 23, "symbol": "↑"}
        }
        mock_summaries.return_value = []
        mock_digest.return_value = None

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["llm_summary"] is None

    @patch('report_data.get_user_keywords')
    @patch('report_data.get_keyword_stats')
    @patch('report_data.get_llm_summaries')
    @patch('report_data.generate_weekly_digest')
    def test_handles_zero_sentiment_total(self, mock_digest, mock_summaries, mock_stats, mock_keywords):
        mock_conn = MagicMock()
        mock_keywords.return_value = ["new_keyword"]
        mock_stats.return_value = {
            "keyword": "new_keyword",
            "posts_24h": 0,
            "posts_7d": 0,
            "posts_previous_7d": 0,
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0, "total": 0},
            "trend": {"direction": "stable", "percent": 0, "symbol": "→"}
        }
        mock_summaries.return_value = []
        mock_digest.return_value = None

        result = get_user_report_data(mock_conn, user_id=1)

        assert result["totals"]["avg_positive_sentiment"] == 0

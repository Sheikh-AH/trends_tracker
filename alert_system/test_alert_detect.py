# pylint: skip-file
import pytest
from unittest.mock import patch, MagicMock
from alert_detect import get_all_keywords, get_post_count_last_5_min, get_average_5_min_count_last_24h, detect_spikes


class TestGetAllKeywords:

    @patch('alert_detect.get_db_connection')
    def test_returns_list_of_keywords(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('matcha',), ('coffee',), ('tea',)]
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_all_keywords()

        assert result == ['matcha', 'coffee', 'tea']
        assert isinstance(result, list)

    @patch('alert_detect.get_db_connection')
    def test_returns_empty_list_when_no_keywords(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_all_keywords()

        assert result == []

    @patch('alert_detect.get_db_connection')
    def test_closes_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        get_all_keywords()

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()


class TestGetPostCountLast5Min:

    @patch('alert_detect.get_db_connection')
    def test_returns_count(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (15,)
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_post_count_last_5_min('matcha')

        assert result == 15

    @patch('alert_detect.get_db_connection')
    def test_returns_zero_when_no_posts(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_post_count_last_5_min('matcha')

        assert result == 0

    @patch('alert_detect.get_db_connection')
    def test_closes_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.return_value.cursor.return_value = mock_cursor

        get_post_count_last_5_min('matcha')

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()


class TestGetAverage5MinCountLast24h:

    @patch('alert_detect.get_db_connection')
    def test_returns_average(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            288,)  # 288 posts = 1 per 5 min period
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_average_5_min_count_last_24h('matcha')

        assert result == 1.0

    @patch('alert_detect.get_db_connection')
    def test_returns_zero_when_no_posts(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_average_5_min_count_last_24h('matcha')

        assert result == 0

    @patch('alert_detect.get_db_connection')
    def test_closes_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.return_value.cursor.return_value = mock_cursor

        get_average_5_min_count_last_24h('matcha')

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()


class TestDetectSpikes:

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_detects_spike_when_count_is_double_average(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = ['matcha']
        mock_current.return_value = 20
        mock_average.return_value = 5

        result = detect_spikes()

        assert len(result) == 1
        assert result[0]['keyword'] == 'matcha'
        assert result[0]['current_count'] == 20
        assert result[0]['average_count'] == 5

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_no_spike_when_count_below_threshold(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = ['matcha']
        mock_current.return_value = 3  # Below minimum of 5
        mock_average.return_value = 1

        result = detect_spikes()

        assert len(result) == 0

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_no_spike_when_count_not_double_average(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = ['matcha']
        mock_current.return_value = 8
        mock_average.return_value = 5  # 8 is not 2x 5

        result = detect_spikes()

        assert len(result) == 0

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_no_spike_when_average_is_zero(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = ['matcha']
        mock_current.return_value = 10
        mock_average.return_value = 0

        result = detect_spikes()

        assert len(result) == 0

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_returns_empty_list_when_no_keywords(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = []

        result = detect_spikes()

        assert result == []

    @patch('alert_detect.get_average_5_min_count_last_24h')
    @patch('alert_detect.get_post_count_last_5_min')
    @patch('alert_detect.get_all_keywords')
    def test_detects_multiple_spikes(self, mock_keywords, mock_current, mock_average):
        mock_keywords.return_value = ['matcha', 'coffee', 'tea']
        mock_current.side_effect = [20, 5, 15]
        mock_average.side_effect = [5, 5, 5]

        result = detect_spikes()

        assert len(result) == 2
        assert result[0]['keyword'] == 'matcha'
        assert result[1]['keyword'] == 'tea'

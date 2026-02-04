import pytest
from unittest.mock import patch, MagicMock
from gt_extract import get_keywords_from_db, get_search_volume, extract


class TestGetKeywordsFromDb:

    @patch('gt_extract.get_db_connection')
    def test_returns_set_of_keywords(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('matcha',), ('coffee',), ('tea',)]
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_keywords_from_db()

        assert result == {'matcha', 'coffee', 'tea'}
        assert isinstance(result, set)

    @patch('gt_extract.get_db_connection')
    def test_returns_empty_set_when_no_keywords(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_keywords_from_db()

        assert result == set()

    @patch('gt_extract.get_db_connection')
    def test_closes_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        get_keywords_from_db()

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()


class TestGetSearchVolume:

    def test_returns_empty_list_when_no_keywords(self):
        result = get_search_volume(set())

        assert result == []

    @patch('gt_extract.TrendReq')
    def test_returns_search_volume_for_keywords(self, mock_pytrends):
        mock_instance = MagicMock()
        mock_pytrends.return_value = mock_instance

        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.columns = ['matcha']
        mock_df.__getitem__ = lambda self, key: MagicMock(mean=lambda: 75.5)
        mock_instance.interest_over_time.return_value = mock_df

        result = get_search_volume({'matcha'})

        assert len(result) == 1
        assert result[0]['keyword_value'] == 'matcha'
        assert result[0]['search_volume'] == 75

    @patch('gt_extract.TrendReq')
    def test_handles_api_error(self, mock_pytrends):
        mock_instance = MagicMock()
        mock_pytrends.return_value = mock_instance
        mock_instance.build_payload.side_effect = Exception("API Error")

        result = get_search_volume({'matcha'})

        assert result == []


class TestExtract:

    @patch('gt_extract.get_search_volume')
    @patch('gt_extract.get_keywords_from_db')
    def test_extract_returns_raw_data(self, mock_get_keywords, mock_get_volume):
        mock_get_keywords.return_value = {'matcha', 'coffee'}
        mock_get_volume.return_value = [
            {'keyword_value': 'matcha', 'search_volume': 75},
            {'keyword_value': 'coffee', 'search_volume': 90}
        ]

        result = extract()

        assert len(result) == 2
        mock_get_keywords.assert_called_once()
        mock_get_volume.assert_called_once_with({'matcha', 'coffee'})

    @patch('gt_extract.get_search_volume')
    @patch('gt_extract.get_keywords_from_db')
    def test_extract_handles_empty_keywords(self, mock_get_keywords, mock_get_volume):
        mock_get_keywords.return_value = set()
        mock_get_volume.return_value = []

        result = extract()

        assert result == []

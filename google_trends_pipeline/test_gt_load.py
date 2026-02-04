# pylint: skip-file
"""Test suite for gt_load module."""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from gt_load import get_db_connection, load


class TestGetDbConnection:

    @patch('gt_load.psycopg2.connect')
    def test_connects_with_env_variables(self, mock_connect):
        with patch.dict('os.environ', {
            'DB_HOST': 'test-host',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass'
        }):
            get_db_connection()

            mock_connect.assert_called_once_with(
                host='test-host',
                port='5432',
                dbname='test_db',
                user='test_user',
                password='test_pass'
            )


class TestLoad:

    def test_returns_none_when_no_data(self):
        result = load([])

        assert result is None

    def test_returns_none_when_none(self):
        result = load(None)

        assert result is None

    @patch('gt_load.get_db_connection')
    def test_inserts_single_record(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        data = [{
            'keyword_value': 'matcha',
            'search_volume': 75,
            'trend_date': datetime.now(timezone.utc)
        }]

        load(data)

        assert mock_cursor.execute.call_count == 1
        mock_conn.return_value.commit.assert_called_once()

    @patch('gt_load.get_db_connection')
    def test_inserts_multiple_records(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        data = [
            {'keyword_value': 'matcha', 'search_volume': 75,
                'trend_date': datetime.now(timezone.utc)},
            {'keyword_value': 'coffee', 'search_volume': 90,
                'trend_date': datetime.now(timezone.utc)},
            {'keyword_value': 'tea', 'search_volume': 60,
                'trend_date': datetime.now(timezone.utc)}
        ]

        load(data)

        assert mock_cursor.execute.call_count == 3

    @patch('gt_load.get_db_connection')
    def test_closes_cursor_and_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        data = [{'keyword_value': 'matcha', 'search_volume': 75,
                 'trend_date': datetime.now(timezone.utc)}]

        load(data)

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()

    @patch('gt_load.get_db_connection')
    def test_executes_correct_sql(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        test_time = datetime.now(timezone.utc)
        data = [{'keyword_value': 'matcha',
                 'search_volume': 75, 'trend_date': test_time}]

        load(data)

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert 'INSERT INTO google_trends' in sql
        assert 'keyword_value' in sql
        assert 'search_volume' in sql
        assert 'trend_date' in sql
        assert params == ('matcha', 75, test_time)

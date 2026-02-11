# pylint: disable=missing-function-docstring
# pylint: disable=unused-argument
"""Tests for bs_load module with database mocking."""

from bs_load import get_db_connection, upload_batch, load_data
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

import pytest

# Add load directory to path
sys.path.insert(0, str(Path(__file__).parent))


class TestGetDbConnection:
    """Tests for get_db_connection function."""

    @patch('bs_load.psycopg2.connect')
    def test_successful_connection(self, mock_connect):
        """Test successful database connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        config = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
        }

        result = get_db_connection(config)

        assert result == mock_conn
        mock_connect.assert_called_once_with(
            dbname="testdb",
            user="testuser",
            password="testpass",
            host="localhost",
            port="5432"
        )

    @patch('bs_load.psycopg2.connect')
    def test_connection_missing_port_default(self, mock_connect):
        """Test that port defaults to 5432 if not provided."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        config = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_HOST": "localhost",
        }

        get_db_connection(config)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[1]
        assert call_args["port"] == 5432

    @patch('bs_load.psycopg2.connect')
    def test_connection_custom_port(self, mock_connect):
        """Test connection with custom port."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        config = {
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
        }

        get_db_connection(config)

        call_args = mock_connect.call_args[1]
        assert call_args["port"] == "3306"


class TestUploadBatch:
    """Tests for upload_batch function."""

    def test_empty_batch(self):
        """Test that empty batch is handled gracefully."""
        mock_conn = Mock()
        upload_batch([], mock_conn)

        # Should return early without cursor operations
        mock_conn.cursor.assert_not_called()

    @patch('bs_load.execute_batch')
    def test_single_post_batch(self, mock_execute_batch):
        """Test uploading a batch with a single post."""
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        posts = [
            {
                "post_uri": "at://did:plc:123/app.bsky.feed.post/abc123",
                "commit": {
                    "record": {
                        "createdAt": "2026-02-03T15:00:00Z",
                        "text": "Test post",
                        "reply": {}
                    }
                },
                "did": "did:plc:123",
                "sentiment": 0.5,
                "matching_keywords": ["test"],
                "repost_uri": None
            }
        ]

        upload_batch(posts, mock_conn)

        mock_conn.cursor.assert_called_once()
        assert mock_execute_batch.call_count == 2  # posts + matches
        mock_conn.commit.assert_called_once()

    @patch('bs_load.execute_batch')
    def test_batch_with_multiple_posts(self, mock_execute_batch):
        """Test uploading batch with multiple posts."""
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        posts = [
            {
                "post_uri": "at://did:plc:1/app.bsky.feed.post/a1",
                "commit": {"record": {"createdAt": "2026-02-03T15:00:00Z", "text": "Post 1", "reply": {}}},
                "did": "did:plc:1",
                "sentiment": 0.5,
                "matching_keywords": ["keyword1"],
                "repost_uri": None
            },
            {
                "post_uri": "at://did:plc:2/app.bsky.feed.post/a2",
                "commit": {"record": {"createdAt": "2026-02-03T15:01:00Z", "text": "Post 2", "reply": {}}},
                "did": "did:plc:2",
                "sentiment": -0.3,
                "matching_keywords": ["keyword2"],
                "repost_uri": None
            },
        ]

        upload_batch(posts, mock_conn)

        # execute_batch should be called twice (once for posts, once for matches)
        assert mock_execute_batch.call_count == 2
        mock_conn.commit.assert_called_once()

    @patch('bs_load.execute_batch')
    def test_batch_with_multiple_keywords_per_post(self, mock_execute_batch):
        """Test that multiple keywords per post create multiple match rows."""
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        posts = [
            {
                "post_uri": "at://did:plc:1/app.bsky.feed.post/a1",
                "commit": {"record": {"createdAt": "2026-02-03T15:00:00Z", "text": "Post", "reply": {}}},
                "did": "did:plc:1",
                "sentiment": 0.5,
                "matching_keywords": ["kw1", "kw2", "kw3"],
                "repost_uri": None
            }
        ]

        upload_batch(posts, mock_conn)

        # execute_batch called twice
        assert mock_execute_batch.call_count == 2
        mock_conn.commit.assert_called_once()

    @patch('bs_load.execute_batch')
    def test_batch_with_reply_uri(self, mock_execute_batch):
        """Test post with reply_uri information."""
        mock_cursor = MagicMock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor

        posts = [
            {
                "post_uri": "at://did:plc:1/app.bsky.feed.post/a1",
                "commit": {
                    "record": {
                        "createdAt": "2026-02-03T15:00:00Z",
                        "text": "Reply text",
                        "reply": {
                            "parent": {
                                "uri": "at://did:plc:0/app.bsky.feed.post/parent123"
                            }
                        }
                    }
                },
                "did": "did:plc:1",
                "sentiment": 0.0,
                "matching_keywords": ["test"],
                "repost_uri": None
            }
        ]

        upload_batch(posts, mock_conn)

        mock_execute_batch.assert_called()
        mock_conn.commit.assert_called_once()


class TestLoadData:
    """Tests for load_data function."""

    @patch('bs_load.upload_batch')
    def test_load_small_batch(self, mock_upload):
        """Test loading data smaller than batch size."""
        mock_conn = Mock()

        posts = [
            {
                "post_uri": "at://did:plc:1/app.bsky.feed.post/a1",
                "commit": {"record": {"createdAt": "2026-02-03T15:00:00Z", "text": "Post", "reply": {}}},
                "did": "did:plc:1",
                "sentiment": 0.5,
                "matching_keywords": ["test"],
                "repost_uri": None
            }
        ]

        def mock_post_generator():
            for post in posts:
                yield post

        load_data(mock_conn, mock_post_generator(), batch_size=100)

        # Should flush remaining batch at end
        mock_upload.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_load_exact_batch_size(self):
        """Test loading data exactly equal to batch size."""
        mock_conn = Mock()

        # Create mock posts generator
        posts = [
            {
                "post_uri": f"at://did:plc:{i}/app.bsky.feed.post/a{i}",
                "commit": {"record": {"createdAt": "2026-02-03T15:00:00Z", "text": f"Post {i}", "reply": {}}},
                "did": f"did:plc:{i}",
                "sentiment": 0.0,
                "matching_keywords": ["test"],
                "repost_uri": None
            }
            for i in range(5)
        ]

        def mock_post_generator():
            for post in posts:
                yield post

        with patch('bs_load.upload_batch') as mock_upload:
            load_data(mock_conn, mock_post_generator(), batch_size=5)

            # Should call upload_batch at least once
            assert mock_upload.call_count >= 1

    def test_load_multiple_batches(self):
        """Test loading data larger than batch size triggers multiple uploads."""
        mock_conn = Mock()

        posts = [
            {
                "post_uri": f"at://did:plc:{i}/app.bsky.feed.post/a{i}",
                "commit": {"record": {"createdAt": "2026-02-03T15:00:00Z", "text": f"Post {i}", "reply": {}}},
                "did": f"did:plc:{i}",
                "sentiment": 0.0,
                "matching_keywords": ["test"],
                "repost_uri": None
            }
            for i in range(10)
        ]

        def mock_post_generator():
            for post in posts:
                yield post

        with patch('bs_load.upload_batch') as mock_upload:
            load_data(mock_conn, mock_post_generator(), batch_size=3)

            # With 10 posts and batch size 3: 3 full batches + 1 remaining = 4 calls
            assert mock_upload.call_count == 4

    def test_load_closes_connection(self):
        """Test that connection is closed after loading."""
        mock_conn = Mock()
        posts = []

        def mock_post_generator():
            return
            yield

        load_data(mock_conn, mock_post_generator(), batch_size=100)

        mock_conn.close.assert_called_once()

    def test_load_with_empty_generator(self):
        """Test loading with empty post generator."""
        mock_conn = Mock()

        def empty_generator():
            return
            yield

        with patch('bs_load.upload_batch') as mock_upload:
            load_data(mock_conn, empty_generator(), batch_size=100)

            mock_upload.assert_not_called()
            mock_conn.close.assert_called_once()

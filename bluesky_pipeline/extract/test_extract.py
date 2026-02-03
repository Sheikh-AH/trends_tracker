# pylint: skip-file
"""Tests for extract module."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from extract import keyword_match, BlueskyFirehose


@pytest.fixture
def sample_keywords():
    """Fixture providing a set of sample keywords."""
    return {"python", "coding", "bluesky"}


@pytest.fixture
def empty_keywords():
    """Fixture providing an empty keyword set."""
    return set()


@pytest.fixture
def sample_message():
    """Fixture providing a sample Bluesky message."""
    return {
        "did": "did:plc:example123",
        "time_us": 1234567890000000,
        "kind": "commit",
        "commit": {
            "cid": "bafy123...",
            "rev": "0",
            "operation": "create",
            "collection": "app.bsky.feed.post",
            "rkey": "abc123",
            "record": {
                "text": "Hello from Bluesky!",
                "createdAt": "2026-02-03T12:00:00.000Z",
            }
        }
    }


class TestKeywordMatchBasic:
    """Basic tests for keyword_match function."""

    def test_single_keyword_found(self, sample_keywords):
        """Test that matching keywords are returned."""
        result = keyword_match(sample_keywords, "I love python")
        assert result == {"python"}

    def test_multiple_keywords_found(self, sample_keywords):
        """Test that multiple matching keywords are returned."""
        result = keyword_match(sample_keywords, "python coding on bluesky")
        assert result == {"python", "coding", "bluesky"}

    def test_no_keywords_found(self, sample_keywords):
        """Test that None is returned when no keywords match."""
        result = keyword_match(sample_keywords, "I love coffee")
        assert result is None

    def test_empty_keywords_set(self):
        """Test that empty keywords set returns None."""
        result = keyword_match(set(), "Any text here")
        assert result is None

    def test_empty_post_text(self, sample_keywords):
        """Test that empty post text returns None."""
        result = keyword_match(sample_keywords, "")
        assert result is None

    def test_both_empty(self):
        """Test that both empty keywords and text returns None."""
        result = keyword_match(set(), "")
        assert result is None


class TestKeywordMatchCaseSensitivity:
    """Tests for case-insensitive matching behavior."""

    def test_lowercase_keyword_uppercase_text(self, sample_keywords):
        """Test matching with lowercase keyword and uppercase text."""
        result = keyword_match(sample_keywords, "PYTHON is great")
        assert result == {"python"}

    def test_uppercase_keyword_lowercase_text(self, sample_keywords):
        """Test matching with uppercase keyword and lowercase text."""
        result = keyword_match(sample_keywords, "i love coding")
        assert result == {"coding"}

    def test_mixed_case_matching(self, sample_keywords):
        """Test matching with mixed case in both keyword and text."""
        result = keyword_match(sample_keywords, "PyThOn programming")
        assert result == {"python"}


class TestKeywordMatchParametrized:
    """Parametrized tests for various scenarios."""

    @pytest.mark.parametrize(
        "keywords,text,expected",
        [
            ({"hello"}, "hello world", {"hello"}),
            ({"hello"}, "goodbye world", None),
            ({"hello", "world"}, "hello there", {"hello"}),
            ({"hello", "world"}, "world today", {"world"}),
            ({"hello", "world"}, "goodbye friend", None),
            ({"trend", "viral"}, "This is trending now", {"trend"}),
            ({"trend", "viral"}, "The movie went viral", {"viral"}),
            ({"trend", "viral"}, "Normal boring post", None),
        ],
    )
    def test_keyword_matching_scenarios(self, keywords, text, expected):
        """Test various keyword matching scenarios."""
        assert keyword_match(keywords, text) == expected

    @pytest.mark.parametrize(
        "keywords,text,expected",
        [
            ({"a"}, "abcdef", {"a"}),
            ({"xyz"}, "abcxyzdef", {"xyz"}),
            ({"zzz"}, "abcdef", None),
            ({"test"}, "This is a test.", {"test"}),
            ({"test"}, "This is testing.", {"test"}),
        ],
    )
    def test_substring_matching(self, keywords, text, expected):
        """Test that keywords match as substrings in text."""
        assert keyword_match(keywords, text) == expected


class TestKeywordMatchEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_keyword_at_beginning(self, sample_keywords):
        """Test matching when keyword is at the beginning."""
        result = keyword_match(sample_keywords, "python is great")
        assert result == {"python"}

    def test_keyword_at_end(self, sample_keywords):
        """Test matching when keyword is at the end."""
        result = keyword_match(sample_keywords, "I love coding")
        assert result == {"coding"}

    def test_keyword_in_middle(self, sample_keywords):
        """Test matching when keyword is in the middle."""
        result = keyword_match(sample_keywords, "Some text bluesky more text")
        assert result == {"bluesky"}

    def test_multiple_keywords_in_text(self, sample_keywords):
        """Test when text contains multiple keywords."""
        result = keyword_match(sample_keywords, "python and bluesky coding")
        assert result == {"python", "bluesky", "coding"}

    def test_keyword_with_special_characters(self):
        """Test matching keywords with special characters."""
        keywords = {"c++", "c#"}
        result1 = keyword_match(keywords, "I code in c++")
        result2 = keyword_match(keywords, "I code in c#")
        assert result1 == {"c++"}
        assert result2 == {"c#"}

    def test_whitespace_handling(self, sample_keywords):
        """Test that keywords match correctly with whitespace."""
        result1 = keyword_match(sample_keywords, "   python   ")
        result2 = keyword_match(sample_keywords, "\tpython\n")
        result3 = keyword_match(sample_keywords, " coding ")
        assert result1 == {"python"}
        assert result2 == {"python"}
        assert result3 == {"coding"}


class TestBlueskyFirehoseInit:
    """Tests for BlueskyFirehose initialization."""

    def test_init_default_uri(self):
        """Test initialization with default URI."""
        firehose = BlueskyFirehose()
        assert firehose.uri == "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"
        assert firehose.websocket is None

    def test_init_custom_uri(self):
        """Test initialization with custom URI."""
        custom_uri = "wss://custom.example.com/jetstream"
        firehose = BlueskyFirehose(uri=custom_uri)
        assert firehose.uri == custom_uri
        assert firehose.websocket is None


class TestBlueskyFirehoseWebsocket:
    """Tests for websocket connection management."""

    @pytest.mark.asyncio
    async def test_get_websocket_creates_connection(self):
        """Test that get_websocket creates a new connection."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            ws = await firehose.get_websocket()
            assert ws == mock_ws
            assert firehose.websocket == mock_ws

    @pytest.mark.asyncio
    async def test_get_websocket_reuses_connection(self):
        """Test that get_websocket reuses existing connection."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()
        firehose.websocket = mock_ws

        ws = await firehose.get_websocket()
        assert ws == mock_ws

    @pytest.mark.asyncio
    async def test_close_websocket(self):
        """Test that close properly closes the websocket."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()
        firehose.websocket = mock_ws

        await firehose.close()
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_websocket(self):
        """Test that close handles None websocket gracefully."""
        firehose = BlueskyFirehose()
        # Should not raise an error
        await firehose.close()


class TestBlueskyFirehoseStreamMessages:
    """Tests for message streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_messages_yields_parsed_json(self, sample_message):
        """Test that stream_messages yields parsed JSON messages."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = json.dumps(sample_message)
        firehose.websocket = mock_ws

        # Get one message from generator
        gen = firehose.stream_messages()
        msg = await gen.__anext__()

        assert msg == sample_message
        mock_ws.recv.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_messages_handles_json_error(self, capfd):
        """Test that stream_messages handles JSON decode errors."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()
        # First call returns invalid JSON, second returns valid
        mock_ws.recv.side_effect = [
            "invalid json",
            json.dumps({"valid": "message"}),
        ]
        firehose.websocket = mock_ws

        gen = firehose.stream_messages()
        # Should skip invalid and return valid
        msg = await gen.__anext__()

        assert msg == {"valid": "message"}
        captured = capfd.readouterr()
        assert "Error decoding JSON" in captured.out

    @pytest.mark.asyncio
    async def test_stream_messages_handles_connection_error(self):
        """Test that stream_messages recovers from connection errors."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()

        # First recv raises error, then succeeds
        valid_msg = json.dumps({"test": "message"})
        mock_ws.recv.side_effect = [
            Exception("Connection error"),
            valid_msg,
        ]

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            firehose.websocket = mock_ws
            gen = firehose.stream_messages()

            # Should recover and yield message
            msg = await gen.__anext__()
            assert msg == {"test": "message"}
            # Connection is recreated after error, so websocket should exist
            assert firehose.websocket is not None

    @pytest.mark.asyncio
    async def test_stream_messages_multiple_messages(self, sample_message):
        """Test that stream_messages can yield multiple messages."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()

        messages = [json.dumps(sample_message) for _ in range(3)]
        mock_ws.recv.side_effect = messages
        firehose.websocket = mock_ws

        gen = firehose.stream_messages()
        results = []
        for _ in range(3):
            msg = await gen.__anext__()
            results.append(msg)

        assert len(results) == 3
        assert all(msg == sample_message for msg in results)


class TestBlueskyFirehoseGetOneMessage:
    """Tests for getting a single message."""

    @pytest.mark.asyncio
    async def test_get_one_message_returns_first_message(self, sample_message):
        """Test that get_one_message returns the first message."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = json.dumps(sample_message)
        firehose.websocket = mock_ws

        msg = await firehose.get_one_message()

        assert msg == sample_message

    @pytest.mark.asyncio
    async def test_get_one_message_stops_after_one(self, sample_message):
        """Test that get_one_message stops after receiving one message."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()

        # Set up two potential messages
        messages = [json.dumps(sample_message), json.dumps(sample_message)]
        mock_ws.recv.side_effect = messages
        firehose.websocket = mock_ws

        msg = await firehose.get_one_message()

        # Should only call recv once
        assert mock_ws.recv.call_count == 1
        assert msg == sample_message

    @pytest.mark.asyncio
    async def test_get_one_message_handles_invalid_json(self, sample_message):
        """Test that get_one_message skips invalid messages."""
        firehose = BlueskyFirehose()
        mock_ws = AsyncMock()

        # First invalid, then valid
        mock_ws.recv.side_effect = [
            "not json",
            json.dumps(sample_message),
        ]
        firehose.websocket = mock_ws

        msg = await firehose.get_one_message()

        # Should skip invalid and return valid
        assert msg == sample_message

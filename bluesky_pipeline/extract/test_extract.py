# pylint: skip-file
"""Tests for extract module."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from extract import BlueskyFirehose


@pytest.fixture
def firehose():
    """Fixture providing a BlueskyFirehose instance."""
    return BlueskyFirehose()


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
    """Basic tests for keyword_match method."""

    def test_single_keyword_found(self, firehose, sample_keywords):
        """Test that matching keywords are returned."""
        result = firehose.keyword_match(sample_keywords, "I love python")
        assert result == {"python"}

    def test_multiple_keywords_found(self, firehose, sample_keywords):
        """Test that multiple matching keywords are returned."""
        result = firehose.keyword_match(sample_keywords, "python coding on bluesky")
        assert result == {"python", "coding", "bluesky"}

    def test_no_keywords_found(self, firehose, sample_keywords):
        """Test that None is returned when no keywords match."""
        result = firehose.keyword_match(sample_keywords, "I love coffee")
        assert result is None

    def test_empty_keywords_set(self, firehose):
        """Test that empty keywords set returns None."""
        result = firehose.keyword_match(set(), "Any text here")
        assert result is None

    def test_empty_post_text(self, firehose, sample_keywords):
        """Test that empty post text returns None."""
        result = firehose.keyword_match(sample_keywords, "")
        assert result is None

    def test_both_empty(self, firehose):
        """Test that both empty keywords and text returns None."""
        result = firehose.keyword_match(set(), "")
        assert result is None


class TestKeywordMatchCaseSensitivity:
    """Tests for case-insensitive matching behavior."""

    def test_lowercase_keyword_uppercase_text(self, firehose, sample_keywords):
        """Test matching with lowercase keyword and uppercase text."""
        result = firehose.keyword_match(sample_keywords, "PYTHON is great")
        assert result == {"python"}

    def test_uppercase_keyword_lowercase_text(self, firehose, sample_keywords):
        """Test matching with uppercase keyword and lowercase text."""
        result = firehose.keyword_match(sample_keywords, "i love coding")
        assert result == {"coding"}

    def test_mixed_case_matching(self, firehose, sample_keywords):
        """Test matching with mixed case in both keyword and text."""
        result = firehose.keyword_match(sample_keywords, "PyThOn programming")
        assert result == {"python"}


class TestKeywordMatchWordBoundary:
    """Tests for word boundary matching with regex."""

    def test_whole_word_match(self, firehose):
        """Test that keywords match as whole words only."""
        keywords = {"ice"}
        # Should NOT match 'ice' in 'nice'
        result = firehose.keyword_match(keywords, "She was nice")
        assert result is None

    def test_whole_word_with_punctuation(self, firehose):
        """Test that keywords match with punctuation boundaries."""
        keywords = {"ice"}
        result = firehose.keyword_match(keywords, "I like ice.")
        assert result == {"ice"}

    def test_word_at_boundaries(self, firehose):
        """Test matching at word boundaries."""
        keywords = {"test"}
        assert firehose.keyword_match(keywords, "test case") == {"test"}
        assert firehose.keyword_match(keywords, "the test") == {"test"}
        assert firehose.keyword_match(keywords, "testing") is None  # 'test' is prefix, not word
        assert firehose.keyword_match(keywords, "retest") is None  # 'test' is suffix, not word

    @pytest.mark.parametrize(
        "keywords,text,expected",
        [
            ({"hello"}, "hello world", {"hello"}),
            ({"hello"}, "goodbye world", None),
            ({"hello"}, "helloworld", None),  # No word boundary
            ({"hello", "world"}, "hello there", {"hello"}),
            ({"hello", "world"}, "world today", {"world"}),
            ({"hello", "world"}, "goodbye friend", None),
            ({"trend"}, "This is trending now", None),  # 'trend' is prefix of 'trending'
            ({"trend"}, "The movie went viral", None),
            ({"viral"}, "The movie went viral", {"viral"}),
        ],
    )
    def test_word_boundary_scenarios(self, firehose, keywords, text, expected):
        """Test various word boundary matching scenarios."""
        assert firehose.keyword_match(keywords, text) == expected

    def test_special_characters_in_keywords(self, firehose):
        """Test matching keywords with special characters."""
        keywords = {"c++", "c#"}
        result1 = firehose.keyword_match(keywords, "I code in c++")
        result2 = firehose.keyword_match(keywords, "I code in c#")
        assert result1 == {"c++"}
        assert result2 == {"c#"}

    def test_whitespace_handling(self, firehose, sample_keywords):
        """Test that keywords match correctly with whitespace."""
        result1 = firehose.keyword_match(sample_keywords, "   python   ")
        result2 = firehose.keyword_match(sample_keywords, "\tpython\n")
        result3 = firehose.keyword_match(sample_keywords, " coding ")
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

class TestParseAtUri:
    """Tests for _parse_at_uri method."""

    def test_parse_valid_at_uri(self, firehose):
        """Test parsing a valid AT URI."""
        at_uri = "at://did:plc:xyz123/app.bsky.feed.post/abc456"
        result = firehose._parse_at_uri(at_uri)
        assert result == "abc456"

    def test_parse_at_uri_with_trailing_slash(self, firehose):
        """Test parsing AT URI with trailing slash."""
        at_uri = "at://did:plc:xyz123/app.bsky.feed.post/abc456/"
        result = firehose._parse_at_uri(at_uri)
        assert result == ""  # Trailing slash creates empty last component

    def test_parse_at_uri_simple(self, firehose):
        """Test parsing AT URI with just rkey."""
        at_uri = "at://did:plc:xyz123/abc456"
        result = firehose._parse_at_uri(at_uri)
        assert result == "abc456"

    def test_parse_empty_at_uri(self, firehose):
        """Test parsing empty AT URI."""
        result = firehose._parse_at_uri("")
        assert result is None

    def test_parse_none_at_uri(self, firehose):
        """Test parsing None as AT URI."""
        result = firehose._parse_at_uri(None)
        assert result is None

    def test_parse_malformed_at_uri(self, firehose):
        """Test parsing malformed AT URI."""
        result = firehose._parse_at_uri("not-an-at-uri")
        assert result == "not-an-at-uri"  # Returns the last component

    @pytest.mark.parametrize(
        "at_uri,expected",
        [
            ("at://did:plc:123/app.bsky.feed.post/xyz789", "xyz789"),
            ("at://did:plc:abc/reply/def123", "def123"),
            ("uri-with-only-one-part", "uri-with-only-one-part"),
        ],
    )
    def test_parse_at_uri_parametrized(self, firehose, at_uri, expected):
        """Test parsing various AT URI formats."""
        result = firehose._parse_at_uri(at_uri)
        assert result == expected


class TestComposePostUrl:
    """Tests for compose_post_url method."""

    def test_compose_basic_url(self, firehose):
        """Test composing a basic post URL."""
        did = "did:plc:user123"
        rkey = "post456"
        result = firehose.compose_post_url(did, rkey)
        assert result == "https://bsky.app/profile/did:plc:user123/post/post456"

    def test_compose_url_with_special_characters(self, firehose):
        """Test composing URL with special characters in rkey."""
        did = "did:plc:abcd1234"
        rkey = "3mdxip34o4g2y"
        result = firehose.compose_post_url(did, rkey)
        assert result == "https://bsky.app/profile/did:plc:abcd1234/post/3mdxip34o4g2y"

    def test_compose_url_format(self, firehose):
        """Test that composed URL follows Bluesky format."""
        did = "did:plc:test"
        rkey = "abc123"
        url = firehose.compose_post_url(did, rkey)
        assert url.startswith("https://bsky.app/profile/")
        assert "/post/" in url
        assert did in url
        assert rkey in url

    @pytest.mark.parametrize(
        "did,rkey,expected_url",
        [
            ("did:plc:user1", "post1", "https://bsky.app/profile/did:plc:user1/post/post1"),
            ("did:key:abc", "xyz789", "https://bsky.app/profile/did:key:abc/post/xyz789"),
        ],
    )
    def test_compose_url_parametrized(self, firehose, did, rkey, expected_url):
        """Test composing URLs with various DIDs and rkeys."""
        result = firehose.compose_post_url(did, rkey)
        assert result == expected_url


class TestAddPostUrlToMessage:
    """Tests for _add_post_url_to_message method."""

    def test_add_url_to_valid_message(self, firehose, sample_message):
        """Test adding URL to a valid message."""
        # Modify sample_message to include rkey in commit
        sample_message["commit"]["rkey"] = "abc123"
        result = firehose._add_post_url_to_message(sample_message)

        assert "post_url" in result
        assert "did:plc:example123" in result["post_url"]
        assert "abc123" in result["post_url"]

    def test_add_url_missing_did(self, firehose, sample_message):
        """Test that URL is not added if DID is missing."""
        msg = dict(sample_message)  # Create a fresh copy
        msg["commit"] = dict(msg["commit"])  # Deep copy commit dict
        msg["commit"]["rkey"] = "abc123"
        msg.pop("did", None)
        result = firehose._add_post_url_to_message(msg)

        assert "post_url" not in result

    def test_add_url_missing_rkey(self, firehose, sample_message):
        """Test that URL is not added if rkey is missing."""
        msg = dict(sample_message)  # Create a fresh copy
        msg["commit"] = dict(msg["commit"])  # Deep copy commit dict
        msg["commit"].pop("rkey", None)  # Ensure no rkey
        result = firehose._add_post_url_to_message(msg)
        assert "post_url" not in result

    def test_add_url_returns_modified_message(self, firehose, sample_message):
        """Test that the method returns the modified message."""
        msg = dict(sample_message)  # Create a fresh copy
        msg["commit"] = dict(msg["commit"])  # Deep copy commit dict
        msg["commit"]["rkey"] = "xyz"
        result = firehose._add_post_url_to_message(msg)

        # Should have all original fields plus new one
        assert result["did"] == msg["did"]
        assert result["post_url"] is not None

    def test_add_url_preserves_other_fields(self, firehose):
        """Test that adding URL doesn't modify other message fields."""
        message = {
            "did": "did:plc:test123",
            "commit": {
                "rkey": "rkey789",
                "record": {"text": "test post"}
            },
            "custom_field": "custom_value"
        }
        result = firehose._add_post_url_to_message(message)

        assert result["custom_field"] == "custom_value"
        assert result["commit"]["record"]["text"] == "test post"
        assert "post_url" in result

    def test_add_url_handles_missing_nested_fields(self, firehose):
        """Test that method handles missing nested fields gracefully."""
        message = {
            "did": "did:plc:test",
            "commit": {}
        }
        result = firehose._add_post_url_to_message(message)

        # Should not crash and return message unchanged
        assert "post_url" not in result
        assert result == message


class TestGetPostType:
    """Tests for get_post_type method."""

    def test_post_type_standalone_post(self, firehose):
        """Test that a post without reply is classified as 'post'."""
        message = {
            "commit": {
                "record": {
                    "text": "This is a standalone post"
                }
            }
        }
        result = firehose.get_post_type(message)
        assert result == "post"

    def test_post_type_direct_reply(self, firehose):
        """Test that a direct reply (parent == root) is classified as 'reply'."""
        message = {
            "commit": {
                "record": {
                    "text": "This is a reply",
                    "reply": {
                        "parent": {
                            "uri": "at://did:plc:abc/app.bsky.feed.post/xyz123"
                        },
                        "root": {
                            "uri": "at://did:plc:abc/app.bsky.feed.post/xyz123"
                        }
                    }
                }
            }
        }
        result = firehose.get_post_type(message)
        assert result == "reply"

    def test_post_type_comment(self, firehose):
        """Test that a comment (parent != root) is classified as 'comment'."""
        message = {
            "commit": {
                "record": {
                    "text": "This is a comment on a reply",
                    "reply": {
                        "parent": {
                            "uri": "at://did:plc:user1/app.bsky.feed.post/reply123"
                        },
                        "root": {
                            "uri": "at://did:plc:user2/app.bsky.feed.post/original123"
                        }
                    }
                }
            }
        }
        result = firehose.get_post_type(message)
        assert result == "comment"

    def test_post_type_empty_reply_field(self, firehose):
        """Test that a post with empty reply field is classified as 'post'."""
        message = {
            "commit": {
                "record": {
                    "text": "Post with empty reply",
                    "reply": {}
                }
            }
        }
        result = firehose.get_post_type(message)
        assert result == "post"

    def test_post_type_missing_record(self, firehose):
        """Test that missing record returns 'unknown'."""
        message = {
            "commit": {}
        }
        result = firehose.get_post_type(message)
        assert result == "unknown"

    def test_post_type_missing_commit(self, firehose):
        """Test that missing commit returns 'unknown'."""
        message = {}
        result = firehose.get_post_type(message)
        assert result == "unknown"

    def test_post_type_malformed_message(self, firehose):
        """Test that malformed message returns 'unknown'."""
        message = None
        result = firehose.get_post_type(message)
        assert result == "unknown"

    @pytest.mark.parametrize(
        "message,expected_type",
        [
            # Standalone post
            ({"commit": {"record": {"text": "post"}}}, "post"),
            # Direct reply - parent == root
            (
                {
                    "commit": {
                        "record": {
                            "reply": {
                                "parent": {"uri": "at://did:plc:a/post/123"},
                                "root": {"uri": "at://did:plc:a/post/123"}
                            }
                        }
                    }
                },
                "reply"
            ),
            # Comment - parent != root
            (
                {
                    "commit": {
                        "record": {
                            "reply": {
                                "parent": {"uri": "at://did:plc:a/post/123"},
                                "root": {"uri": "at://did:plc:b/post/456"}
                            }
                        }
                    }
                },
                "comment"
            ),
        ],
    )
    def test_post_type_parametrized(self, firehose, message, expected_type):
        """Test various post type scenarios."""
        result = firehose.get_post_type(message)
        assert result == expected_type

    def test_post_type_with_actual_jetstream_message(self, firehose, sample_message):
        """Test with actual Jetstream message structure (sample_message has reply)."""
        msg = dict(sample_message)
        msg["commit"] = dict(msg["commit"])
        msg["commit"]["record"] = {
            "reply": {
                "parent": {"uri": "at://did:plc:a/post/123"},
                "root": {"uri": "at://did:plc:a/post/123"}
            }
        }
        result = firehose.get_post_type(msg)
        assert result == "reply"

    def test_post_type_preserves_message(self, firehose):
        """Test that get_post_type doesn't modify the original message."""
        message = {
            "commit": {"record": {"text": "test"}}
        }
        original = dict(message)
        firehose.get_post_type(message)
        assert message == original
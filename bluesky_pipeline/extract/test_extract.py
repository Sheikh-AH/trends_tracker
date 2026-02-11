# pylint: skip-file
"""Tests for extract module."""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import json

import pytest

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from extract import keyword_match, compile_keyword_patterns, get_keywords, stream_messages, stream_filtered_messages


class TestKeywordMatchBasic:
    """Basic tests for keyword_match function."""

    def test_single_keyword_found(self, compiled_patterns):
        """Test that matching keywords are returned."""
        result = keyword_match(compiled_patterns, "I love python")
        assert result == {"python"}

    def test_multiple_keywords_found(self, compiled_patterns):
        """Test that multiple matching keywords are returned."""
        result = keyword_match(compiled_patterns, "python coding on bluesky")
        assert result == {"python", "coding", "bluesky"}

    def test_no_keywords_found(self, compiled_patterns):
        """Test that None is returned when no keywords match."""
        result = keyword_match(compiled_patterns, "I love coffee")
        assert result is None

    def test_empty_keywords_set(self):
        """Test that empty keywords dict returns None."""
        result = keyword_match({}, "Any text here")
        assert result is None

    def test_empty_post_text(self, compiled_patterns):
        """Test that empty post text returns None."""
        result = keyword_match(compiled_patterns, "")
        assert result is None

    def test_both_empty(self):
        """Test that both empty keywords and text returns None."""
        result = keyword_match({}, "")
        assert result is None


class TestKeywordMatchCaseSensitivity:
    """Tests for case-insensitive matching behavior."""

    def test_lowercase_keyword_uppercase_text(self, compiled_patterns):
        """Test matching with lowercase keyword and uppercase text."""
        result = keyword_match(compiled_patterns, "PYTHON is great")
        assert result == {"python"}

    def test_uppercase_keyword_lowercase_text(self, compiled_patterns):
        """Test matching with uppercase keyword and lowercase text."""
        result = keyword_match(compiled_patterns, "i love coding")
        assert result == {"coding"}

    def test_mixed_case_matching(self, compiled_patterns):
        """Test matching with mixed case in both keyword and text."""
        result = keyword_match(compiled_patterns, "PyThOn programming")
        assert result == {"python"}


class TestKeywordMatchWordBoundary:
    """Tests for word boundary matching with regex."""

    def test_whole_word_match(self):
        """Test that keywords match as whole words only."""
        keywords = {"ice"}
        patterns = compile_keyword_patterns(keywords)
        # Should NOT match 'ice' in 'nice'
        result = keyword_match(patterns, "She was nice")
        assert result is None

    def test_whole_word_with_punctuation(self):
        """Test that keywords match with punctuation boundaries."""
        keywords = {"ice"}
        patterns = compile_keyword_patterns(keywords)
        result = keyword_match(patterns, "I like ice.")
        assert result == {"ice"}

    def test_word_at_boundaries(self):
        """Test matching at word boundaries (prefix matching enabled)."""
        keywords = {"test"}
        patterns = compile_keyword_patterns(keywords)
        assert keyword_match(patterns, "test case") == {"test"}
        assert keyword_match(patterns, "the test") == {"test"}
        assert keyword_match(patterns, "testing") == {
            "test"}  # 'test' matches as prefix
        # 'test' requires word boundary before it
        assert keyword_match(patterns, "retest") is None

    @pytest.mark.parametrize(
        "keywords,text,expected",
        [
            ({"hello"}, "hello world", {"hello"}),
            ({"hello"}, "goodbye world", None),  # 'hello' matches as prefix
            ({"hello", "world"}, "hello there", {"hello"}),
            ({"hello", "world"}, "world today", {"world"}),
            ({"hello", "world"}, "goodbye friend", None),
            ({"trend"}, "This is trending now", {"trend"}),
            ({"trend"}, "The movie went viral", None),
            ({"viral"}, "The movie went viral", {"viral"}),
        ],
    )
    def test_word_boundary_scenarios(self, keywords, text, expected):
        """Test various word boundary matching scenarios with prefix matching."""
        patterns = compile_keyword_patterns(keywords)
        assert keyword_match(patterns, text) == expected

    def test_special_characters_in_keywords(self):
        """Test matching keywords with special characters."""
        keywords = {"c++", "c#"}
        patterns = compile_keyword_patterns(keywords)
        result1 = keyword_match(patterns, "I code in c++")
        result2 = keyword_match(patterns, "I code in c#")
        assert result1 == {"c++"}
        assert result2 == {"c#"}

    def test_whitespace_handling(self, compiled_patterns):
        """Test that keywords match correctly with whitespace."""
        result1 = keyword_match(compiled_patterns, "   python   ")
        result2 = keyword_match(compiled_patterns, "\tpython\n")
        result3 = keyword_match(compiled_patterns, " coding ")
        assert result1 == {"python"}
        assert result2 == {"python"}
        assert result3 == {"coding"}


class TestCompileKeywordPatterns:
    """Tests for compile_keyword_patterns function."""

    def test_empty_keywords_set(self):
        """Test compiling empty keywords set."""
        patterns = compile_keyword_patterns(set())
        assert patterns == {}

    def test_single_keyword(self):
        """Test compiling a single keyword."""
        patterns = compile_keyword_patterns({"python"})
        assert "python" in patterns
        assert hasattr(patterns["python"], "search")  # Check it's a compiled regex

    def test_multiple_keywords(self):
        """Test compiling multiple keywords."""
        keywords = {"python", "javascript", "rust"}
        patterns = compile_keyword_patterns(keywords)
        assert len(patterns) == 3
        assert all(kw in patterns for kw in keywords)

    def test_keyword_with_special_chars(self):
        """Test that special regex chars are escaped."""
        keywords = {"c++", "c#", ".net"}
        patterns = compile_keyword_patterns(keywords)
        # Verify patterns compile without regex error
        assert len(patterns) == 3
        for pattern in patterns.values():
            assert hasattr(pattern, "search")

    def test_keyword_case_preservation(self):
        """Test that keyword original case is preserved in dict key."""
        keywords = {"Python", "JAVASCRIPT"}
        patterns = compile_keyword_patterns(keywords)
        assert "Python" in patterns
        assert "JAVASCRIPT" in patterns


class TestIntegrationExtract:
    """Integration tests for extract functions."""

    def test_keyword_flow_with_compile_and_match(self):
        """Test full flow: compile keywords then match against text."""
        keywords = {"trending", "viral"}
        patterns = compile_keyword_patterns(keywords)

        text1 = "This is trending now"
        text2 = "This went viral on social media"
        text3 = "Nothing special here"

        assert keyword_match(patterns, text1) == {"trending"}
        assert keyword_match(patterns, text2) == {"viral"}
        assert keyword_match(patterns, text3) is None

    def test_unicode_keyword_matching(self):
        """Test that unicode keywords are handled correctly."""
        keywords = {"café", "naïve", "résumé"}
        patterns = compile_keyword_patterns(keywords)

        result = keyword_match(patterns, "I love café culture")
        assert "café" in result

    def test_number_in_keyword(self):
        """Test keywords containing numbers."""
        keywords = {"5g", "covid19", "2024"}
        patterns = compile_keyword_patterns(keywords)

        assert keyword_match(patterns, "5g technology") == {"5g"}
        assert keyword_match(patterns, "covid19 pandemic") == {"covid19"}
        assert keyword_match(patterns, "2024 elections") == {"2024"}


class TestGetKeywords:
    """Tests for get_keywords function."""

    def test_get_keywords_with_results(self):
        """Test fetching keywords from database with results."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("python",),
            ("javascript",),
            ("bluesky",)
        ]

        result = get_keywords(mock_cursor)

        assert result == {"python", "javascript", "bluesky"}
        mock_cursor.execute.assert_called_once_with("SELECT keyword_value FROM keywords")

    def test_get_keywords_empty_database(self):
        """Test fetching keywords when database has no keywords."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []

        result = get_keywords(mock_cursor)

        assert result == set()
        mock_cursor.execute.assert_called_once()

    def test_get_keywords_single_result(self):
        """Test fetching a single keyword."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("trending",)]

        result = get_keywords(mock_cursor)

        assert result == {"trending"}

    def test_get_keywords_with_special_chars(self):
        """Test fetching keywords with special characters."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("c++",),
            ("c#",),
            (".net",)
        ]

        result = get_keywords(mock_cursor)

        assert "c++" in result
        assert "c#" in result
        assert ".net" in result


class TestStreamMessages:
    """Tests for stream_messages function."""

    @patch('extract.websocket.create_connection')
    def test_stream_messages_closes_on_error(self, mock_create_connection):
        """Test that websocket closes even on error."""
        mock_ws = MagicMock()
        mock_create_connection.return_value = mock_ws
        mock_ws.recv.side_effect = Exception("Connection error")

        with pytest.raises(Exception):
            list(stream_messages())

        mock_ws.close.assert_called_once()

class TestStreamFilteredMessages:
    """Tests for stream_filtered_messages function."""

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_no_matching_posts(self, mock_time, mock_stream):
        """Test streaming when no posts match keywords."""
        mock_time.side_effect = [0, 1, 2]  # Simulate time progression

        # Non-matching post
        mock_stream.return_value = iter([
            {
                "kind": "commit",
                "commit": {
                    "record": {"text": "random coffee talk"}
                }
            }
        ])

        def keyword_fetcher():
            return {"python", "coding"}

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 0

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_with_matching_keywords(self, mock_time, mock_stream):
        """Test streaming with matching keywords."""
        mock_time.side_effect = [0, 1, 2]  # Simulate time progression

        # Matching post
        mock_stream.return_value = iter([
            {
                "kind": "commit",
                "commit": {
                    "record": {"text": "I love python programming"}
                }
            }
        ])

        def keyword_fetcher():
            return {"python"}

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 1
        assert results[0]["matching_keywords"] == ["python"]

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_multiple_keywords_match(self, mock_time, mock_stream):
        """Test post matching multiple keywords."""
        mock_time.side_effect = [0, 1, 2]

        mock_stream.return_value = iter([
            {
                "kind": "commit",
                "commit": {
                    "record": {"text": "python coding on bluesky"}
                }
            }
        ])

        def keyword_fetcher():
            return {"python", "coding", "bluesky"}

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 1
        assert set(results[0]["matching_keywords"]) == {"python", "coding", "bluesky"}

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_ignores_non_commit(self, mock_time, mock_stream):
        """Test that non-commit messages are ignored."""
        mock_time.side_effect = [0, 1, 2, 3]

        mock_stream.return_value = iter([
            {"kind": "identity"},  # Not a commit
            {
                "kind": "commit",
                "commit": {"record": {"text": "python"}}
            }
        ])

        def keyword_fetcher():
            return {"python"}

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 1

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_keyword_refresh(self, mock_time, mock_stream):
        """Test that keywords are refreshed periodically."""
        # Simulate time passing beyond refresh interval (60s)
        mock_time.side_effect = [0, 70, 140]

        mock_stream.return_value = iter([
            {"kind": "commit", "commit": {"record": {"text": "python"}}},
            {"kind": "commit", "commit": {"record": {"text": "rust"}}},
        ])

        call_count = [0]

        def keyword_fetcher():
            call_count[0] += 1
            if call_count[0] == 1:
                return {"python"}
            else:
                return {"python", "rust"}

        results = list(stream_filtered_messages(keyword_fetcher))

        # First call returns python, second call adds rust
        assert call_count[0] > 1  # Keyword fetcher was called more than once
        # We should get at least one result matching the keywords
        assert len(results) > 0

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_empty_keywords(self, mock_time, mock_stream):
        """Test streaming when keyword_fetcher returns empty set."""
        mock_time.side_effect = [0, 1, 2]

        mock_stream.return_value = iter([
            {"kind": "commit", "commit": {"record": {"text": "any text"}}}
        ])

        def keyword_fetcher():
            return set()

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 0

    @patch('extract.stream_messages')
    @patch('extract.time.time')
    def test_stream_filtered_messages_case_insensitive(self, mock_time, mock_stream):
        """Test that keyword matching is case-insensitive."""
        mock_time.side_effect = [0, 1, 2]

        mock_stream.return_value = iter([
            {"kind": "commit", "commit": {"record": {"text": "I love PYTHON"}}}
        ])

        def keyword_fetcher():
            return {"python"}

        results = list(stream_filtered_messages(keyword_fetcher))

        assert len(results) == 1
        assert "python" in results[0]["matching_keywords"]

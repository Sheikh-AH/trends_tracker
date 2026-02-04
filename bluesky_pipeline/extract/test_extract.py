# pylint: skip-file
"""Tests for extract module."""

import pytest
from .extract import keyword_match, compile_keyword_patterns


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

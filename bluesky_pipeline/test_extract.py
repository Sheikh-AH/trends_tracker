# pylint: skip-file
"""Tests for extract module."""

import pytest
from extract import keyword_match


@pytest.fixture
def sample_keywords():
    """Fixture providing a set of sample keywords."""
    return {"python", "coding", "bluesky"}


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


class TestKeywordMatchWordBoundary:
    """Tests for word boundary matching with regex."""

    def test_whole_word_match(self):
        """Test that keywords match as whole words only."""
        keywords = {"ice"}
        # Should NOT match 'ice' in 'nice'
        result = keyword_match(keywords, "She was nice")
        assert result is None

    def test_whole_word_with_punctuation(self):
        """Test that keywords match with punctuation boundaries."""
        keywords = {"ice"}
        result = keyword_match(keywords, "I like ice.")
        assert result == {"ice"}

    def test_word_at_boundaries(self):
        """Test matching at word boundaries (prefix matching enabled)."""
        keywords = {"test"}
        assert keyword_match(keywords, "test case") == {"test"}
        assert keyword_match(keywords, "the test") == {"test"}
        assert keyword_match(keywords, "testing") == {"test"}  # 'test' matches as prefix
        assert keyword_match(keywords, "retest") is None  # 'test' requires word boundary before it

    @pytest.mark.parametrize(
        "keywords,text,expected",
        [
            ({"hello"}, "hello world", {"hello"}),
            ({"hello"}, "goodbye world", None),
            ({"hello"}, "helloworld", {"hello"}),  # 'hello' matches as prefix
            ({"hello", "world"}, "hello there", {"hello"}),
            ({"hello", "world"}, "world today", {"world"}),
            ({"hello", "world"}, "goodbye friend", None),
            ({"trend"}, "This is trending now", {"trend"}),  # 'trend' matches as prefix of 'trending'
            ({"trend"}, "The movie went viral", None),
            ({"viral"}, "The movie went viral", {"viral"}),
        ],
    )
    def test_word_boundary_scenarios(self, keywords, text, expected):
        """Test various word boundary matching scenarios with prefix matching."""
        assert keyword_match(keywords, text) == expected

    def test_special_characters_in_keywords(self):
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
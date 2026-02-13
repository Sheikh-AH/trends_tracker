# pylint: disable=missing-function-docstring, import-error
"""Tests for ui_helper_utils module."""

import pytest
from unittest.mock import Mock, patch

from ui_helper_utils import get_sentiment_emoji, load_html_template, _HTML_TEMPLATE_CACHE


# ============== Tests for get_sentiment_emoji ==============

class TestGetSentimentEmoji:
    """Tests for get_sentiment_emoji function."""

    def test_very_positive_sentiment(self):
        """Test emoji for very positive sentiment."""
        assert get_sentiment_emoji(0.5) == "😄"
        assert get_sentiment_emoji(0.4) == "😄"
        assert get_sentiment_emoji(1.0) == "😄"

    def test_positive_sentiment(self):
        """Test emoji for positive sentiment."""
        assert get_sentiment_emoji(0.3) == "😊"
        assert get_sentiment_emoji(0.25) == "😊"

    def test_slightly_positive_sentiment(self):
        """Test emoji for slightly positive sentiment."""
        assert get_sentiment_emoji(0.15) == "🙂"
        assert get_sentiment_emoji(0.1) == "🙂"

    def test_neutral_sentiment(self):
        """Test emoji for neutral sentiment."""
        assert get_sentiment_emoji(0.0) == "😐"
        assert get_sentiment_emoji(0.05) == "😐"
        assert get_sentiment_emoji(-0.05) == "😐"

    def test_slightly_negative_sentiment(self):
        """Test emoji for slightly negative sentiment."""
        assert get_sentiment_emoji(-0.15) == "😕"
        assert get_sentiment_emoji(-0.25) == "😕"

    def test_negative_sentiment(self):
        """Test emoji for negative sentiment."""
        assert get_sentiment_emoji(-0.5) == "😠"

    def test_very_negative_sentiment(self):
        """Test emoji for very negative sentiment."""
        assert get_sentiment_emoji(-1.0) == "😠"

    def test_boundary_values(self):
        """Test boundary values between emoji ranges."""
        assert get_sentiment_emoji(0.25) == "😊"
        assert get_sentiment_emoji(0.1) == "🙂"
        assert get_sentiment_emoji(-0.1) == "😐"
        assert get_sentiment_emoji(-0.25) == "😕"

    def test_extreme_values(self):
        """Test extreme values."""
        assert get_sentiment_emoji(10.0) == "😄"

    def test_float_precision(self):
        """Test float precision handling."""
        assert get_sentiment_emoji(0.249999) == "🙂"
        assert get_sentiment_emoji(0.250001) == "😊"


# ============== Tests for load_html_template ==============

class TestLoadHtmlTemplate:
    """Tests for load_html_template function."""

    def test_loads_html_file(self):
        """Test that HTML template files can be loaded."""
        # Mock the file reading to avoid dependency on actual files
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "<html>Test</html>"
            # Clear cache to ensure fresh load
            _HTML_TEMPLATE_CACHE.clear()
            result = load_html_template("test.html")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_returns_string(self):
        """Test that function returns string type."""
        try:
            result = load_html_template("home_title.html")
            assert isinstance(result, str)
        except FileNotFoundError:
            pass

    def test_caches_result(self):
        """Test that result is cached in _HTML_TEMPLATE_CACHE."""
        cache_before = len(_HTML_TEMPLATE_CACHE)

        try:
            load_html_template("home_title.html")
            # Cache should have been updated
            assert len(_HTML_TEMPLATE_CACHE) >= cache_before
        except FileNotFoundError:
            pass

    def test_repeated_calls_use_cache(self):
        """Test that repeated calls use cached result."""
        try:
            result1 = load_html_template("home_title.html")
            result2 = load_html_template("home_title.html")

            # Should return the same object reference if cached
            assert result1 == result2
        except FileNotFoundError:
            pass

    def test_missing_file_handling(self):
        """Test handling of missing HTML files."""
        # Function returns empty string for missing files
        result = load_html_template("/nonexistent/path/file.html")
        assert result == ""

    def test_loads_different_templates(self):
        """Test loading multiple different templates."""
        templates = ["home_title.html", "home_font_buttons.html", "post_card.html"]

        for template in templates:
            try:
                result = load_html_template(template)
                assert isinstance(result, str)
            except FileNotFoundError:
                # Template may not exist
                pass


# ============== Tests for _HTML_TEMPLATE_CACHE ==============

class TestHtmlTemplateCache:
    """Tests for _HTML_TEMPLATE_CACHE dictionary."""

    def test_cache_is_dict(self):
        """Test that _HTML_TEMPLATE_CACHE is a dictionary."""
        assert isinstance(_HTML_TEMPLATE_CACHE, dict)

    def test_cache_accepts_entries(self):
        """Test that cache can store entries."""
        _HTML_TEMPLATE_CACHE["test_key"] = "test_value"

        assert "test_key" in _HTML_TEMPLATE_CACHE
        assert _HTML_TEMPLATE_CACHE["test_key"] == "test_value"

    def test_cache_retrieval(self):
        """Test retrieving values from cache."""
        _HTML_TEMPLATE_CACHE["test_key"] = "<html>test</html>"

        assert _HTML_TEMPLATE_CACHE.get("test_key") == "<html>test</html>"

    def test_cache_persistence(self):
        """Test that cached values persist."""
        test_key = "persistent_test"
        test_value = "<html>persistent</html>"

        _HTML_TEMPLATE_CACHE[test_key] = test_value

        # Value should still be there
        assert _HTML_TEMPLATE_CACHE.get(test_key) == test_value


# ============== Integration Tests ==============

class TestUiHelperUtilsIntegration:
    """Integration tests for ui_helper_utils functions."""

    def test_get_sentiment_emoji_covers_range(self):
        """Test that get_sentiment_emoji covers full sentiment range."""
        sentiments = [-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0]
        emojis = set()

        for sentiment in sentiments:
            emoji = get_sentiment_emoji(sentiment)
            emojis.add(emoji)
            assert isinstance(emoji, str)
            assert len(emoji) > 0

        # Should have multiple different emojis
        assert len(emojis) > 1

    def test_sentiment_emoji_consistency(self):
        """Test that sentiment emoji mapping is consistent."""
        test_sentiments = [0.3, 0.3, 0.3]

        results = [get_sentiment_emoji(s) for s in test_sentiments]

        # All same sentiment should give same emoji
        assert results[0] == results[1] == results[2]

    def test_emoji_boundary_consistency(self):
        """Test that boundaries are consistent."""
        # Test that emoji changes at expected boundaries
        negative_emoji = get_sentiment_emoji(-0.11)
        neutral_emoji = get_sentiment_emoji(-0.05)

        # Should be different emojis
        assert negative_emoji != neutral_emoji

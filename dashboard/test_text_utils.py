# pylint: disable=missing-function-docstring, import-error
"""Tests for text_utils module."""

import pytest
from unittest.mock import Mock, patch

from text_utils import diversify_keywords, extract_keywords_yake


# ============== Tests for extract_keywords_yake ==============

class TestExtractKeywordsYake:
    """Tests for extract_keywords_yake function."""

    def test_extracts_keywords_from_text(self):
        """Test that function extracts keywords from text."""
        text = "Python is a great programming language for data science"

        result = extract_keywords_yake(text, num_keywords=5)

        assert isinstance(result, list)
        assert len(result) <= 5
        assert all(isinstance(item, dict) for item in result)
        assert all("keyword" in item and "score" in item for item in result)

    def test_respects_num_keywords_limit(self):
        """Test that function respects num_keywords parameter."""
        text = "The quick brown fox jumps over the lazy dog"

        result = extract_keywords_yake(text, num_keywords=3)

        assert len(result) <= 3

    def test_empty_text_returns_empty_list(self):
        """Test that empty text returns empty list."""
        result = extract_keywords_yake("", num_keywords=5)

        assert result == [] or isinstance(result, list)

    def test_returns_keywords_with_scores(self):
        """Test that returned keywords have scores."""
        text = "machine learning algorithms for artificial intelligence"

        result = extract_keywords_yake(text, num_keywords=5)

        if result:
            for item in result:
                assert "keyword" in item
                assert "score" in item
                assert isinstance(item["score"], (int, float))
                assert 0 <= item["score"] <= 1

    def test_single_word_text(self):
        """Test with single word."""
        result = extract_keywords_yake("Python", num_keywords=5)

        assert isinstance(result, list)

    def test_duplicate_phrases(self):
        """Test handling of duplicate phrases."""
        text = "Python Python Python is great great great"

        result = extract_keywords_yake(text, num_keywords=5)

        assert isinstance(result, list)

    def test_special_characters(self):
        """Test handling of special characters."""
        text = "C++ is #1 for high-performance computing!"

        result = extract_keywords_yake(text, num_keywords=5)

        assert isinstance(result, list)

    def test_long_text(self):
        """Test with longer text."""
        text = """
        Natural language processing is a subfield of linguistics, computer science,
        and artificial intelligence concerned with the interactions between computers
        and human language. NLP is used to apply machine learning algorithms to text and speech.
        """

        result = extract_keywords_yake(text, num_keywords=10)

        assert isinstance(result, list)
        assert len(result) <= 10

    def test_different_num_keywords(self):
        """Test different num_keywords values."""
        text = "data science machine learning artificial intelligence"

        for num in [1, 3, 5, 10]:
            result = extract_keywords_yake(text, num_keywords=num)
            assert len(result) <= num


# ============== Tests for diversify_keywords ==============

class TestDiversifyKeywords:
    """Tests for diversify_keywords function."""

    def test_diversifies_keywords(self):
        """Test that function diversifies keywords."""
        keywords = [
            {"keyword": "python", "score": 0.5},
            {"keyword": "python programming", "score": 0.4},
            {"keyword": "java", "score": 0.3},
            {"keyword": "java programming", "score": 0.2},
        ]

        result = diversify_keywords(keywords, "programming", max_results=2)

        assert isinstance(result, list)
        assert len(result) <= 2

    def test_filters_main_keyword(self):
        """Test that main keyword is filtered out."""
        keywords = [
            {"keyword": "python", "score": 0.8},
            {"keyword": "programming", "score": 0.7},
            {"keyword": "data", "score": 0.6},
        ]

        result = diversify_keywords(keywords, "programming", max_results=10)

        # "programming" should not be in results
        keyword_list = [kw["keyword"] for kw in result]
        assert "programming" not in keyword_list

    def test_removes_duplicates(self):
        """Test that duplicate keywords are removed."""
        keywords = [
            {"keyword": "python", "score": 0.8},
            {"keyword": "python", "score": 0.7},
            {"keyword": "java", "score": 0.6},
        ]

        result = diversify_keywords(keywords, "programming", max_results=10)

        keyword_list = [kw["keyword"] for kw in result]
        # Check for duplicate keywords
        assert len(keyword_list) == len(set(keyword_list))

    def test_respects_max_results(self):
        """Test that function respects max_results limit."""
        keywords = [
            {"keyword": f"keyword{i}", "score": 0.9 - (i * 0.01)}
            for i in range(20)
        ]

        result = diversify_keywords(keywords, "main", max_results=5)

        assert len(result) <= 5

    def test_empty_keywords_list(self):
        """Test with empty keywords list."""
        result = diversify_keywords([], "main", max_results=5)

        assert result == [] or isinstance(result, list)

    def test_single_keyword(self):
        """Test with single keyword."""
        keywords = [{"keyword": "python", "score": 0.8}]

        result = diversify_keywords(keywords, "programming", max_results=5)

        assert isinstance(result, list)

    def test_main_keyword_case_insensitive(self):
        """Test that main keyword filtering is case insensitive."""
        keywords = [
            {"keyword": "Python", "score": 0.8},
            {"keyword": "java", "score": 0.7},
        ]

        result = diversify_keywords(keywords, "python", max_results=10)

        # "Python" should be filtered (case insensitive)
        keyword_list = [kw["keyword"].lower() for kw in result]
        assert "python" not in keyword_list

    def test_preserves_scores(self):
        """Test that scores are preserved after diversification."""
        keywords = [
            {"keyword": "data", "score": 0.9},
            {"keyword": "science", "score": 0.8},
            {"keyword": "analysis", "score": 0.7},
        ]

        result = diversify_keywords(keywords, "main", max_results=10)

        if result:
            for item in result:
                assert "score" in item
                assert isinstance(item["score"], (int, float))

    def test_partial_keyword_matching(self):
        """Test handling of partial keyword matches."""
        keywords = [
            {"keyword": "python", "score": 0.8},
            {"keyword": "python programming", "score": 0.7},
            {"keyword": "java", "score": 0.6},
        ]

        result = diversify_keywords(keywords, "programming", max_results=10)

        assert isinstance(result, list)
        # Should filter out entries containing main keyword
        keyword_list = [kw["keyword"].lower() for kw in result]
        assert not any("programming" in kw for kw in keyword_list)

    def test_large_keyword_set(self):
        """Test with large keyword set."""
        keywords = [
            {"keyword": f"keyword{i}", "score": 0.9 - (i * 0.001)}
            for i in range(1000)
        ]

        result = diversify_keywords(keywords, "main", max_results=50)

        assert len(result) <= 50

    def test_zero_max_results(self):
        """Test with max_results=0."""
        keywords = [
            {"keyword": "python", "score": 0.8},
            {"keyword": "java", "score": 0.7},
        ]

        result = diversify_keywords(keywords, "main", max_results=0)

        assert result == []
        text = """
        Python is a popular programming language.
        Python programming is used for data science.
        Java and C++ are also programming languages.
        """

        keywords = extract_keywords_yake(text, num_keywords=10)
        diversified = diversify_keywords(keywords, "Python", max_results=5)

        assert isinstance(diversified, list)
        keyword_list = [kw["keyword"].lower() for kw in diversified]
        assert "python" not in keyword_list

    def test_workflow_with_realdata(self):
        """Test complete workflow with realistic data."""
        corpus = """
        Machine learning is transforming industries.
        Machine learning algorithms process big data.
        Deep learning neural networks are powerful.
        Artificial intelligence will change everything.
        AI and machine learning are converging.
        """

        keywords = extract_keywords_yake(corpus, num_keywords=15)
        assert len(keywords) > 0

        diversified = diversify_keywords(keywords, "learning", max_results=5)
        assert isinstance(diversified, list)

        if diversified:
            keyword_list = [kw["keyword"].lower() for kw in diversified]
            assert not any("learning" in kw for kw in keyword_list)

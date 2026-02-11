# pylint: disable=missing-function-docstring
# pylint: disable=import-error
"""Tests for bs_transform module."""

import sys
from pathlib import Path

# Add transform directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bs_transform import add_sentiment, add_uri

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def test_add_sentiment():
    analyzer = SentimentIntensityAnalyzer()

    fake_stream = [
        {
            "did": "did:plc:123",
            "commit": {
                "rkey": "abc123",
                "record": {
                    "text": "I love this!",
                    "createdAt": "2026-02-03T15:00:07Z"
                }
            }
        },
        {
            "did": "did:plc:456",
            "commit": {
                "rkey": "def456",
                "record": {
                    "text": "This is terrible",
                    "createdAt": "2026-02-03T15:00:08Z"
                }
            }
        },
        {
            "did": "did:plc:789",
            "commit": {
                "rkey": "ghi789",
                "record": {
                    "text": "Meeting at 3pm",
                    "createdAt": "2026-02-03T15:00:09Z"
                }
            }
        },
    ]

    results = list(add_sentiment(fake_stream, analyzer))

    assert len(results) == 3
    assert results[0]["sentiment"] > 0.05
    assert results[1]["sentiment"] < -0.05
    assert -0.05 < results[2]["sentiment"] < 0.05
    assert results[0]["did"] == "did:plc:123"
    assert results[0]["commit"]["record"]["text"] == "I love this!"


def test_add_uri():
    """Test that add_uri correctly generates post URIs."""
    fake_stream = [
        {
            "did": "did:plc:123",
            "commit": {
                "rkey": "abc123",
                "record": {"text": "First post"}
            }
        },
        {
            "did": "did:plc:456",
            "commit": {
                "rkey": "def456",
                "record": {"text": "Second post"}
            }
        },
    ]

    results = list(add_uri(fake_stream))

    assert len(results) == 2
    assert results[0]["post_uri"] == "at://did:plc:123/app.bsky.feed.post/abc123"
    assert results[1]["post_uri"] == "at://did:plc:456/app.bsky.feed.post/def456"


def test_add_uri_missing_did():
    """Test add_uri when DID is missing."""
    fake_stream = [
        {
            "commit": {
                "rkey": "abc123",
                "record": {"text": "Post without DID"}
            }
        },
    ]

    results = list(add_uri(fake_stream))

    assert len(results) == 1
    assert results[0]["post_uri"] == "at:///app.bsky.feed.post/abc123"


def test_add_uri_missing_rkey():
    """Test add_uri when rkey is missing."""
    fake_stream = [
        {
            "did": "did:plc:123",
            "commit": {
                "record": {"text": "Post without rkey"}
            }
        },
    ]

    results = list(add_uri(fake_stream))

    assert len(results) == 1
    assert results[0]["post_uri"] == "at://did:plc:123/app.bsky.feed.post/"


def test_add_sentiment_empty_text():
    """Test add_sentiment with empty text."""
    analyzer = SentimentIntensityAnalyzer()
    fake_stream = [
        {
            "did": "did:plc:123",
            "commit": {
                "record": {"text": ""}
            }
        },
    ]

    results = list(add_sentiment(fake_stream, analyzer))

    assert len(results) == 1
    assert "sentiment" in results[0]
    assert -1 <= results[0]["sentiment"] <= 1  # Valid sentiment score


def test_sentiment_score_range():
    """Test that sentiment scores are within valid range [-1, 1]."""
    analyzer = SentimentIntensityAnalyzer()
    texts = [
        "I absolutely love this! Best day ever!!!",
        "This is the worst thing I've ever seen",
        "The weather is okay today",
        "Neutral statement without emotion",
    ]

    fake_stream = [{"commit": {"record": {"text": t}}} for t in texts]
    results = list(add_sentiment(fake_stream, analyzer))

    for result in results:
        assert -1 <= result["sentiment"] <= 1, f"Sentiment {result['sentiment']} out of range"


def test_add_uri_chaining():
    """Test that add_uri preserves all original post data."""
    fake_stream = [
        {
            "did": "did:plc:test",
            "commit": {
                "rkey": "testkey",
                "record": {"text": "Test post"}
            },
            "matching_keywords": ["test"],
            "custom_field": "custom_value"
        }
    ]

    results = list(add_uri(fake_stream))

    assert results[0]["matching_keywords"] == ["test"]
    assert results[0]["custom_field"] == "custom_value"
    assert results[0]["post_uri"] == "at://did:plc:test/app.bsky.feed.post/testkey"


def test_transform_pipeline_integration():
    """Test chaining add_sentiment and add_uri together."""
    analyzer = SentimentIntensityAnalyzer()
    fake_stream = [
        {
            "did": "did:plc:123",
            "commit": {
                "rkey": "abc123",
                "record": {"text": "I love this!"}
            }
        }
    ]

    # Chain sentiment then URI
    with_sentiment = list(add_sentiment(fake_stream, analyzer))
    with_uri = list(add_uri(with_sentiment))

    assert len(with_uri) == 1
    assert "sentiment" in with_uri[0]
    assert "post_uri" in with_uri[0]
    assert with_uri[0]["sentiment"] > 0.5
    assert with_uri[0]["post_uri"] == "at://did:plc:123/app.bsky.feed.post/abc123"

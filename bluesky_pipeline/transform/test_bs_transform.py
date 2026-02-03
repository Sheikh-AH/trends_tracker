# pylint: ignore=missing-function-docstring
"""Tests for bs_transform module."""

from bs_transform import add_sentiment


from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def test_add_sentiment():
    analyzer = SentimentIntensityAnalyzer()

    fake_stream = [
        {"type": "app.bsky.feed.post", "createdAt": "2026-02-03T15:00:07Z",
            "text": "I love this!", "did": "123"},
        {"type": "app.bsky.feed.post", "createdAt": "2026-02-03T15:00:07Z",
            "text": "This is terrible", "did": "456"},
        {"type": "app.bsky.feed.post", "createdAt": "2026-02-03T15:00:07Z",
            "text": "Meeting at 3pm", "did": "789"},
    ]

    results = list(add_sentiment(fake_stream, analyzer))

    assert len(results) == 3
    assert len(results[0]) == 5
    assert results[0]["sentiment"] > 0.05
    assert results[1]["sentiment"] < -0.05
    assert -0.05 < results[2]["sentiment"] < 0.05
    assert results[0]["did"] == "123"
    assert results[0]["text"] == "I love this!"

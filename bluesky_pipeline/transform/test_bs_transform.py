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

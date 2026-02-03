"""Shared pytest fixtures for extract tests."""

import pytest
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

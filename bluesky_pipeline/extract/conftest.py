"""Shared pytest fixtures for extract tests."""

import pytest


@pytest.fixture
def sample_keywords():
    """Fixture providing a set of sample keywords."""
    return {"python", "coding", "bluesky"}

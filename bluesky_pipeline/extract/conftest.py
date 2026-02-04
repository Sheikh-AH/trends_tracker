"""Shared pytest fixtures for extract tests."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from extract import compile_keyword_patterns


@pytest.fixture
def sample_keywords():
    """Fixture providing a set of sample keywords."""
    return {"python", "coding", "bluesky"}


@pytest.fixture
def compiled_patterns(sample_keywords):
    """Fixture providing pre-compiled keyword patterns."""
    return compile_keyword_patterns(sample_keywords)

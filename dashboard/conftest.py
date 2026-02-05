"""Shared pytest fixtures for dashboard tests."""

import pytest
from unittest.mock import Mock
import hashlib
from datetime import datetime, timedelta


@pytest.fixture
def mock_cursor():
    """Fixture providing a mock database cursor."""
    return Mock()


@pytest.fixture
def valid_password():
    """Fixture providing a valid password for testing."""
    return "test_password_123"


@pytest.fixture
def password_hash(valid_password):
    """Fixture providing a valid password hash."""
    salt = "test_salt_value"
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        valid_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"{salt}${iterations}${hashed.hex()}"


@pytest.fixture
def user_row(password_hash):
    """Fixture providing a mock user database row (as dictionary from RealDictCursor)."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": password_hash
    }


@pytest.fixture
def user_dict(password_hash):
    """Fixture providing a mock user dictionary."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": password_hash
    }


# ============== Visualization Fixtures ==============

@pytest.fixture
def sample_keyword():
    """Fixture providing a sample keyword for visualization tests."""
    return "matcha"


@pytest.fixture
def sample_keywords():
    """Fixture providing a list of sample keywords."""
    return ["matcha", "boba", "coffee"]


@pytest.fixture
def sample_days():
    """Fixture providing sample days value."""
    return 30


@pytest.fixture
def sample_posts():
    """Fixture providing sample post data for visualizations."""
    return [
        {"text": "I love matcha lattes! ☕", "sentiment": 0.8, "date": datetime.now()},
        {"text": "Matcha is overrated tbh", "sentiment": -0.3, "date": datetime.now() - timedelta(days=1)},
        {"text": "Best matcha spot in town", "sentiment": 0.6, "date": datetime.now() - timedelta(days=2)},
    ]


@pytest.fixture
def sample_word_frequencies():
    """Fixture providing sample word frequencies for word cloud."""
    return {
        "latte": 45,
        "green": 38,
        "tea": 35,
        "healthy": 28,
        "cafe": 22,
        "drink": 18
    }


@pytest.fixture
def sample_daily_sentiments():
    """Fixture providing sample daily sentiment data for calendar heatmap."""
    base_date = datetime(2026, 2, 1)
    return {
        (base_date - timedelta(days=i)).strftime("%Y-%m-%d"): round((i % 10 - 5) / 10, 2)
        for i in range(30)
    }


@pytest.fixture
def sample_keyword_cooccurrence():
    """Fixture providing sample keyword co-occurrence data for network graph."""
    return [
        {"source": "matcha", "target": "latte", "weight": 25},
        {"source": "matcha", "target": "green", "weight": 18},
        {"source": "boba", "target": "milk", "weight": 30},
        {"source": "coffee", "target": "espresso", "weight": 22},
    ]
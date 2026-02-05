"""Shared pytest fixtures for dashboard tests."""

import pytest
from unittest.mock import Mock
import hashlib


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

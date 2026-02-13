# pylint: disable=missing-function-docstring, import-error
"""Tests for auth_utils module."""

import pytest
from unittest.mock import Mock, patch

from auth_utils import generate_password_hash, validate_signup_input, verify_password


# ============== Tests for generate_password_hash ==============

class TestGeneratePasswordHashExtended:
    """Extended tests for generate_password_hash function."""

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = generate_password_hash("password123")
        hash2 = generate_password_hash("password456")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes due to random salt."""
        hash1 = generate_password_hash("password123")
        hash2 = generate_password_hash("password123")

        # Different salts should produce different hashes
        assert hash1 != hash2

    def test_hash_format(self):
        """Test that hash follows expected format: salt$iterations$hash."""
        result = generate_password_hash("password123")
        parts = result.split("$")

        assert len(parts) == 3
        assert parts[1].isdigit()  # iterations should be numeric


# ============== Tests for verify_password ==============

class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_correct(self):
        """Test verify_password with correct password."""
        password = "password123"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, password)

        assert result is True

    def test_verify_password_incorrect(self):
        """Test verify_password with incorrect password."""
        password = "password123"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, "wrong_password")

        assert result is False

    def test_verify_password_empty_password(self):
        """Test verify_password with empty entered password."""
        password = "password123"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, "")

        assert result is False

    def test_verify_password_malformed_hash(self):
        """Test verify_password with malformed hash."""
        malformed_hash = "invalid$hash"

        result = verify_password(malformed_hash, "password")

        assert result is False

    def test_verify_password_invalid_hash(self):
        """Test verify_password with completely invalid hash."""
        invalid_hash = "this_is_not_a_valid_hash"

        result = verify_password(invalid_hash, "password")

        assert result is False

    def test_verify_password_case_sensitive(self):
        """Test that verify_password is case-sensitive."""
        password = "PassWord123"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, "password123")

        assert result is False

    def test_verify_password_consistency(self):
        """Test that verify_password is consistent for same password."""
        password = "password123"
        password_hash = generate_password_hash(password)

        result_correct = verify_password(password_hash, password)
        result_wrong = verify_password(password_hash, "wrong_password")

        assert result_correct is True
        assert result_wrong is False

    def test_verify_password_special_characters(self):
        """Test verify_password with special characters."""
        password = "p@$$w0rd!#%"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, password)

        assert result is True

    def test_verify_password_unicode_characters(self):
        """Test verify_password with unicode characters."""
        password = "пароль123🔐"
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, password)

        assert result is True

    def test_verify_password_long_password(self):
        """Test verify_password with very long password."""
        password = "a" * 1000
        password_hash = generate_password_hash(password)

        result = verify_password(password_hash, password)

        assert result is True

    def test_verify_password_none_hash(self):
        """Test verify_password with None hash."""
        with pytest.raises(AttributeError):
            verify_password(None, "password")

    def test_verify_password_none_password(self):
        """Test verify_password with None password."""
        password_hash = generate_password_hash("password123")

        with pytest.raises(AttributeError):
            verify_password(password_hash, None)


# ============== Tests for validate_signup_input ==============

class TestValidateSignupInputExtended:
    """Extended tests for validate_signup_input function."""

    def test_valid_input(self):
        """Test valid email and password."""
        assert validate_signup_input("test@example.com", "password123") is True

    def test_invalid_email_no_at(self):
        """Test email without @ symbol."""
        assert validate_signup_input("testexample.com", "password123") is False

    def test_invalid_email_no_domain(self):
        """Test email without domain."""
        assert validate_signup_input("test@", "password123") is False

    def test_password_too_short(self):
        """Test password that's too short."""
        assert validate_signup_input("test@example.com", "short") is False

    def test_password_exactly_8_chars(self):
        """Test password with exactly 8 characters (boundary)."""
        # Password must be LONGER than 8, so 8 chars should fail
        assert validate_signup_input("test@example.com", "12345678") is False

    def test_password_9_chars(self):
        """Test password with 9 characters."""
        assert validate_signup_input("test@example.com", "123456789") is True

    def test_empty_email(self):
        """Test empty email."""
        assert validate_signup_input("", "password123") is False

    def test_empty_password(self):
        """Test empty password."""
        assert validate_signup_input("test@example.com", "") is False

    def test_none_values(self):
        """Test None values."""
        assert validate_signup_input(None, "password123") is False
        assert validate_signup_input("test@example.com", None) is False

    def test_email_with_multiple_at_symbols(self):
        """Test email with multiple @ symbols."""
        assert validate_signup_input("test@@example.com", "password123") is False

    def test_email_with_spaces(self):
        """Test email with spaces."""
        assert validate_signup_input("test @example.com", "password123") is False

    def test_password_with_spaces(self):
        """Test password with spaces."""
        assert validate_signup_input("test@example.com", "pass word 123") is True

    def test_email_case_insensitivity(self):
        """Test that email validation handles uppercase."""
        result = validate_signup_input("TEST@EXAMPLE.COM", "password123")
        assert result is True

    def test_valid_email_variations(self):
        """Test various valid email formats."""
        assert validate_signup_input("user@domain.co.uk", "password123") is True
        assert validate_signup_input("user.name@domain.com", "password123") is True
        assert validate_signup_input("user+tag@domain.com", "password123") is True

    def test_password_length_boundary_10_chars(self):
        """Test password with 10 characters."""
        assert validate_signup_input("test@example.com", "1234567890") is True

    def test_password_length_boundary_100_chars(self):
        """Test password with 100 characters."""
        long_password = "a" * 100
        assert validate_signup_input("test@example.com", long_password) is True

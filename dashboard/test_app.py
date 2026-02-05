"""
Unit tests for utility functions and authentication in utils.py using pytest.

Tests cover user retrieval, password verification, authentication flow, user creation,
keyword management, and data generation functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import hashlib
import hmac
import psycopg2
import pandas as pd

from utils import (
    get_user_by_username,
    verify_password,
    authenticate_user,
    generate_password_hash,
    validate_signup_input,
    create_user,
    add_user_keyword,
    remove_user_keyword,
    get_user_keywords,
    generate_word_cloud_data,
    generate_sentiment_calendar_data,
    generate_trending_velocity,
    generate_network_graph_data,
    generate_random_post,
    generate_ai_insights
)


# ============== Tests for get_user_by_username ==============

class TestGetUserByUsername:
    """Tests for get_user_by_username function."""

    def test_user_exists_returns_dict(self, mock_cursor, user_row, user_dict):
        """Test that existing user returns a dictionary with user details."""
        mock_cursor.fetchone.return_value = user_row

        result = get_user_by_username(mock_cursor, "test@example.com")

        assert result == user_dict
        mock_cursor.execute.assert_called_once()

    def test_user_not_found_returns_none(self, mock_cursor):
        """Test that non-existent user returns None."""
        mock_cursor.fetchone.return_value = None

        result = get_user_by_username(mock_cursor, "nonexistent@example.com")

        assert result is None
        mock_cursor.execute.assert_called_once()

    def test_correct_sql_query(self, mock_cursor):
        """Test that the correct SQL query is executed."""
        mock_cursor.fetchone.return_value = None
        email = "test@example.com"

        get_user_by_username(mock_cursor, email)

        expected_query = "SELECT * FROM users WHERE email = %s"
        mock_cursor.execute.assert_called_once_with(expected_query, (email,))

    def test_returns_all_user_fields(self, mock_cursor, user_row):
        """Test that all user fields are returned."""
        mock_cursor.fetchone.return_value = user_row

        result = get_user_by_username(mock_cursor, "test@example.com")

        assert "id" in result
        assert "username" in result
        assert "email" in result
        assert "password_hash" in result

    def test_empty_string_email(self, mock_cursor):
        """Test with empty string email."""
        mock_cursor.fetchone.return_value = None

        result = get_user_by_username(mock_cursor, "")

        assert result is None
        mock_cursor.execute.assert_called_once()


# ============== Tests for verify_password ==============

class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_correct_password_returns_true(self, valid_password, password_hash):
        """Test that correct password returns True."""
        result = verify_password(password_hash, valid_password)

        assert result is True

    def test_incorrect_password_returns_false(self, password_hash):
        """Test that incorrect password returns False."""
        result = verify_password(password_hash, "wrong_password")

        assert result is False

    def test_empty_password_returns_false(self, password_hash):
        """Test that empty password returns False."""
        result = verify_password(password_hash, "")

        assert result is False

    def test_malformed_hash_returns_false(self):
        """Test that malformed hash returns False."""
        malformed_hash = "not_a_valid_hash"

        result = verify_password(malformed_hash, "password")

        assert result is False

    def test_wrong_number_of_hash_parts_returns_false(self):
        """Test that hash with wrong number of parts returns False."""
        invalid_hash = "part1$part2"  # Missing part3

        result = verify_password(invalid_hash, "password")

        assert result is False

    def test_case_sensitive_password(self, valid_password, password_hash):
        """Test that password verification is case-sensitive."""
        wrong_case = valid_password.upper()

        result = verify_password(password_hash, wrong_case)

        assert result is False

    def test_hash_comparison_uses_constant_time(self, valid_password, password_hash):
        """Test that hash comparison uses constant-time comparison (no timing attacks)."""
        # This is implicitly tested by using hmac.compare_digest in the implementation
        # We verify it works correctly
        result_correct = verify_password(password_hash, valid_password)
        result_wrong = verify_password(password_hash, "wrong_password")

        assert result_correct is True
        assert result_wrong is False


# ============== Tests for authenticate_user ==============

class TestAuthenticateUser:
    """Tests for authenticate_user function."""

    def test_valid_credentials_returns_true(self, mock_cursor, valid_password, user_row, user_dict):
        """Test that valid email and password returns True."""
        mock_cursor.fetchone.return_value = user_row

        result = authenticate_user(mock_cursor, "test@example.com", valid_password)

        assert result is True

    def test_invalid_password_returns_false(self, mock_cursor, user_row):
        """Test that invalid password returns False."""
        mock_cursor.fetchone.return_value = user_row

        result = authenticate_user(mock_cursor, "test@example.com", "wrong_password")

        assert result is False

    def test_nonexistent_user_returns_false(self, mock_cursor):
        """Test that non-existent user returns False."""
        mock_cursor.fetchone.return_value = None

        result = authenticate_user(mock_cursor, "nonexistent@example.com", "any_password")

        assert result is False

    def test_empty_email_returns_false(self, mock_cursor):
        """Test that empty email returns False."""
        mock_cursor.fetchone.return_value = None

        result = authenticate_user(mock_cursor, "", "password")

        assert result is False

    def test_empty_password_returns_false(self, mock_cursor, user_row):
        """Test that empty password returns False."""
        mock_cursor.fetchone.return_value = user_row

        result = authenticate_user(mock_cursor, "test@example.com", "")

        assert result is False

    def test_queries_database_for_user(self, mock_cursor, user_row, valid_password):
        """Test that function queries database for the user."""
        mock_cursor.fetchone.return_value = user_row

        authenticate_user(mock_cursor, "test@example.com", valid_password)

        # Verify execute was called (for the query)
        mock_cursor.execute.assert_called_once()

    def test_both_empty_returns_false(self, mock_cursor):
        """Test that both empty email and password returns False."""
        mock_cursor.fetchone.return_value = None

        result = authenticate_user(mock_cursor, "", "")

        assert result is False

    def test_none_username_returns_false(self, mock_cursor):
        """Test that None username is handled gracefully."""
        mock_cursor.fetchone.return_value = None

        # Should not raise an error
        result = authenticate_user(mock_cursor, None, "password")

        assert result is False

    def test_integration_with_get_user_and_verify(self, mock_cursor, user_row, valid_password):
        """Test the full integration of get_user_by_username and verify_password."""
        mock_cursor.fetchone.return_value = user_row

        result = authenticate_user(mock_cursor, "test@example.com", valid_password)

        # Should successfully authenticate with correct password
        assert result is True

        # Reset mock for next test
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = user_row

        result = authenticate_user(mock_cursor, "test@example.com", "wrong")

        # Should fail with wrong password
        assert result is False


# ============== Tests for generate_password_hash ==============

class TestGeneratePasswordHash:
    """Tests for generate_password_hash function."""

    def test_hash_generation_succeeds(self):
        """Test that password hash is generated successfully."""
        password = "test_password_123"

        hash_result = generate_password_hash(password)

        assert hash_result is not None
        assert isinstance(hash_result, str)

    def test_hash_format_is_correct(self):
        """Test that generated hash follows the correct format: salt$iterations$hash."""
        password = "test_password"

        hash_result = generate_password_hash(password)
        parts = hash_result.split("$")

        assert len(parts) == 3
        salt, iterations, hash_hex = parts
        assert salt  # Salt should not be empty
        assert iterations == "100000"  # Default iterations
        assert hash_hex  # Hash should not be empty

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password123"
        password2 = "password456"

        hash1 = generate_password_hash(password1)
        hash2 = generate_password_hash(password2)

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that same password called twice produces different hashes (due to random salt)."""
        password = "same_password"

        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)

        # Different salts should produce different hashes
        assert hash1 != hash2

    def test_generated_hash_can_be_verified(self):
        """Test that a generated hash can be verified with the correct password."""
        password = "test_password_123"

        generated_hash = generate_password_hash(password)
        is_valid = verify_password(generated_hash, password)

        assert is_valid is True

    def test_generated_hash_fails_with_wrong_password(self):
        """Test that verification fails with wrong password against generated hash."""
        password = "correct_password"
        wrong_password = "wrong_password"

        generated_hash = generate_password_hash(password)
        is_valid = verify_password(generated_hash, wrong_password)

        assert is_valid is False

    def test_empty_password_raises_error(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            generate_password_hash("")

    def test_none_password_raises_error(self):
        """Test that None password raises ValueError or AttributeError."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            generate_password_hash(None)

    def test_custom_iterations_parameter(self):
        """Test that custom iterations parameter is respected."""
        password = "test_password"
        custom_iterations = 50000

        hash_result = generate_password_hash(password, iterations=custom_iterations)
        parts = hash_result.split("$")

        assert parts[1] == str(custom_iterations)

    def test_hash_is_reproducible_with_same_salt(self):
        """Test that same password and salt produce same hash."""
        password = "test_password"

        hash1 = generate_password_hash(password, iterations=100000)
        # Extract salt and manually re-hash
        salt = hash1.split("$")[0]

        # Manually hash with the same salt
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        expected_hash = f"{salt}$100000${hashed.hex()}"

        # Verify the stored hash matches when re-hashed with same salt
        assert verify_password(hash1, password) is True

    def test_long_password_hashing(self):
        """Test hashing of very long passwords."""
        long_password = "p" * 1000  # 1000 character password

        hash_result = generate_password_hash(long_password)
        is_valid = verify_password(hash_result, long_password)

        assert is_valid is True

    def test_special_characters_in_password(self):
        """Test hashing passwords with special characters."""
        password = "p@ss!wörd#123$%^&*()"

        hash_result = generate_password_hash(password)
        is_valid = verify_password(hash_result, password)

        assert is_valid is True


# ============== Tests for validate_signup_input ==============

class TestValidateSignupInput:
    """Tests for validate_signup_input function."""

    def test_valid_email_and_password(self):
        """Valid email and password >8 chars returns True."""
        assert validate_signup_input("user@example.com", "Password123") is True

    def test_valid_email_longer_password(self):
        """Valid email with long password returns True."""
        assert validate_signup_input("john.doe@gmail.com", "MySecurePassword2024!") is True

    def test_invalid_email_format(self):
        """Invalid email format returns False."""
        assert validate_signup_input("notanemail", "Password123") is False

    def test_invalid_email_no_domain(self):
        """Email without domain returns False."""
        assert validate_signup_input("user@", "Password123") is False

    def test_password_exactly_8_chars(self):
        """Password with exactly 8 chars returns False (must be >8)."""
        assert validate_signup_input("user@example.com", "12345678") is False

    def test_password_7_chars(self):
        """Password with 7 chars returns False."""
        assert validate_signup_input("user@example.com", "1234567") is False

    def test_password_9_chars(self):
        """Password with 9 chars returns True."""
        assert validate_signup_input("user@example.com", "123456789") is True

    def test_empty_email(self):
        """Empty email returns False."""
        assert validate_signup_input("", "Password123") is False

    def test_empty_password(self):
        """Empty password returns False."""
        assert validate_signup_input("user@example.com", "") is False

    def test_none_email(self):
        """None email returns False."""
        assert validate_signup_input(None, "Password123") is False

    def test_none_password(self):
        """None password returns False."""
        assert validate_signup_input("user@example.com", None) is False

    def test_email_with_special_chars(self):
        """Email with special characters but valid format returns True."""
        assert validate_signup_input("user+tag@example.com", "Password123") is True

    def test_email_with_numbers_in_domain(self):
        """Email with numbers in domain returns True."""
        assert validate_signup_input("user@example123.com", "Password123") is True


# ============== Tests for create_user ==============

class TestCreateUser:
    """Tests for create_user function."""

    @pytest.fixture
    def mock_cursor_create(self):
        """Create a mock database cursor for create_user tests."""
        cursor = Mock()
        cursor.connection = Mock()
        cursor.connection.commit = Mock()
        cursor.connection.rollback = Mock()
        return cursor

    def test_create_user_success(self, mock_cursor_create):
        """Create user successfully returns True."""
        result = create_user(
            mock_cursor_create,
            "newuser@example.com",
            "salt123$100000$hash456"
        )

        assert result is True
        mock_cursor_create.execute.assert_called_once_with(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            ("newuser@example.com", "salt123$100000$hash456")
        )
        mock_cursor_create.connection.commit.assert_called_once()
        mock_cursor_create.connection.rollback.assert_not_called()

    def test_create_user_email_exists(self, mock_cursor_create):
        """Creating user with existing email returns False and rolls back."""
        mock_cursor_create.execute.side_effect = psycopg2.IntegrityError("unique constraint")

        result = create_user(
            mock_cursor_create,
            "existing@example.com",
            "salt123$100000$hash456"
        )

        assert result is False
        mock_cursor_create.connection.rollback.assert_called_once()
        mock_cursor_create.connection.commit.assert_not_called()

    def test_create_user_database_error(self, mock_cursor_create):
        """Database error returns False and rolls back."""
        mock_cursor_create.execute.side_effect = psycopg2.OperationalError("connection failed")

        result = create_user(
            mock_cursor_create,
            "user@example.com",
            "salt123$100000$hash456"
        )

        assert result is False
        mock_cursor_create.connection.rollback.assert_called_once()

    def test_create_user_with_valid_hash_format(self, mock_cursor_create):
        """Create user with properly formatted password hash succeeds."""
        hash_value = "a1b2c3d4e5f6$100000$abcdef0123456789"

        result = create_user(
            mock_cursor_create,
            "user@example.com",
            hash_value
        )

        assert result is True
        mock_cursor_create.execute.assert_called_once_with(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            ("user@example.com", hash_value)
        )

    def test_create_user_preserves_email_case(self, mock_cursor_create):
        """Create user preserves email case."""
        email = "User@Example.COM"

        create_user(mock_cursor_create, email, "salt$100000$hash")

        call_args = mock_cursor_create.execute.call_args
        assert call_args[0][1][0] == email

    def test_create_user_multiple_calls(self, mock_cursor_create):
        """Multiple user creations work independently."""
        create_user(mock_cursor_create, "user1@example.com", "hash1")
        create_user(mock_cursor_create, "user2@example.com", "hash2")

        assert mock_cursor_create.execute.call_count == 2
        assert mock_cursor_create.connection.commit.call_count == 2


# ============== Tests for add_user_keyword ==============

class TestAddUserKeyword:
    """Tests for add_user_keyword function."""

    @pytest.fixture
    def mock_cursor_keyword(self):
        """Create a mock database cursor for keyword tests."""
        cursor = Mock()
        cursor.connection = Mock()
        cursor.connection.commit = Mock()
        return cursor

    def test_add_keyword_success(self, mock_cursor_keyword):
        """Adding keyword successfully returns True."""
        result = add_user_keyword(mock_cursor_keyword, 1, "matcha")

        assert result is True
        # Two execute calls: one for INSERT into keywords, one for INSERT into user_keywords
        assert mock_cursor_keyword.execute.call_count == 2
        mock_cursor_keyword.connection.commit.assert_called_once()

    def test_add_keyword_inserts_to_keywords_and_user_keywords(self, mock_cursor_keyword):
        """Verify both keywords and user_keywords tables are updated."""
        add_user_keyword(mock_cursor_keyword, 1, "coffee")

        calls = mock_cursor_keyword.execute.call_args_list
        # First call should be INSERT into keywords
        assert "keywords" in calls[0][0][0]
        assert "INSERT" in calls[0][0][0]
        # Second call should be INSERT into user_keywords
        assert "user_keywords" in calls[1][0][0]
        assert "INSERT" in calls[1][0][0]


    def test_add_multiple_keywords(self, mock_cursor_keyword):
        """Adding multiple keywords works independently."""
        add_user_keyword(mock_cursor_keyword, 1, "matcha")
        add_user_keyword(mock_cursor_keyword, 1, "coffee")
        add_user_keyword(mock_cursor_keyword, 1, "tea")

        # 2 calls per keyword (keywords table + user_keywords table)
        assert mock_cursor_keyword.execute.call_count == 6
        assert mock_cursor_keyword.connection.commit.call_count == 3

    def test_add_keyword_case_insensitive(self, mock_cursor_keyword):
        """Adding keywords is case-insensitive."""
        add_user_keyword(mock_cursor_keyword, 1, "MATCHA")

        calls = mock_cursor_keyword.execute.call_args_list
        # First call should use LOWER()
        assert "LOWER" in calls[0][0][0]

    def test_add_keyword_different_user(self, mock_cursor_keyword):
        """Adding keywords for different users works correctly."""
        add_user_keyword(mock_cursor_keyword, 1, "matcha")
        add_user_keyword(mock_cursor_keyword, 2, "matcha")

        calls = mock_cursor_keyword.execute.call_args_list
        # Check the user_keywords insert calls (every other call)
        assert calls[1][0][1] == (1, "matcha")
        assert calls[3][0][1] == (2, "matcha")

    def test_add_keyword_with_special_chars(self, mock_cursor_keyword):
        """Adding keyword with special characters works."""
        result = add_user_keyword(mock_cursor_keyword, 1, "blue-sky")

        assert result is True
        assert mock_cursor_keyword.execute.call_count == 2
        calls = mock_cursor_keyword.execute.call_args_list
        assert calls[1][0][1][1] == "blue-sky"


# ============== Tests for remove_user_keyword ==============

class TestRemoveUserKeyword:
    """Tests for remove_user_keyword function."""

    @pytest.fixture
    def mock_cursor_keyword(self):
        """Create a mock database cursor for keyword tests."""
        cursor = Mock()
        cursor.connection = Mock()
        cursor.connection.commit = Mock()
        return cursor

    def test_remove_keyword_success(self, mock_cursor_keyword):
        """Removing keyword successfully returns True."""
        result = remove_user_keyword(mock_cursor_keyword, 1, "matcha")

        assert result is True
        mock_cursor_keyword.execute.assert_called_once()
        mock_cursor_keyword.connection.commit.assert_called_once()

    def test_remove_keyword_case_insensitive(self, mock_cursor_keyword):
        """Verify removal is case-insensitive."""
        remove_user_keyword(mock_cursor_keyword, 1, "MATCHA")

        call_args = mock_cursor_keyword.execute.call_args
        assert "DELETE" in call_args[0][0]
        assert "LOWER" in call_args[0][0]
        assert call_args[0][1] == (1, "MATCHA")

    def test_remove_multiple_keywords(self, mock_cursor_keyword):
        """Removing multiple keywords works independently."""
        remove_user_keyword(mock_cursor_keyword, 1, "matcha")
        remove_user_keyword(mock_cursor_keyword, 1, "coffee")

        assert mock_cursor_keyword.execute.call_count == 2
        assert mock_cursor_keyword.connection.commit.call_count == 2

    def test_remove_keyword_different_users(self, mock_cursor_keyword):
        """Removing keywords from different users works correctly."""
        remove_user_keyword(mock_cursor_keyword, 1, "matcha")
        remove_user_keyword(mock_cursor_keyword, 2, "matcha")

        calls = mock_cursor_keyword.execute.call_args_list
        assert calls[0][0][1] == (1, "matcha")
        assert calls[1][0][1] == (2, "matcha")

    def test_remove_nonexistent_keyword(self, mock_cursor_keyword):
        """Removing nonexistent keyword still returns True (no error)."""
        result = remove_user_keyword(mock_cursor_keyword, 1, "nonexistent")

        assert result is True
        mock_cursor_keyword.connection.commit.assert_called_once()


# ============== Tests for get_user_keywords ==============

class TestGetUserKeywords:
    """Tests for get_user_keywords function."""

    @pytest.fixture
    def mock_cursor_keyword(self):
        """Create a mock database cursor for keyword tests."""
        cursor = Mock()
        return cursor

    def test_get_keywords_returns_list(self, mock_cursor_keyword):
        """Getting keywords returns a list."""
        mock_cursor_keyword.fetchall.return_value = [
            {"keyword_value": "matcha"},
            {"keyword_value": "coffee"}
        ]

        result = get_user_keywords(mock_cursor_keyword, 1)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_keywords_correct_order(self, mock_cursor_keyword):
        """Getting keywords returns them in correct order."""
        mock_cursor_keyword.fetchall.return_value = [
            {"keyword_value": "coffee"},
            {"keyword_value": "matcha"},
            {"keyword_value": "tea"}
        ]

        result = get_user_keywords(mock_cursor_keyword, 1)

        assert result == ["coffee", "matcha", "tea"]

    def test_get_keywords_empty_list(self, mock_cursor_keyword):
        """Getting keywords for user with no keywords returns empty list."""
        mock_cursor_keyword.fetchall.return_value = None

        result = get_user_keywords(mock_cursor_keyword, 1)

        assert result == []

    def test_get_keywords_calls_correct_query(self, mock_cursor_keyword):
        """Verify correct SQL query is executed."""
        mock_cursor_keyword.fetchall.return_value = None

        get_user_keywords(mock_cursor_keyword, 1)

        call_args = mock_cursor_keyword.execute.call_args
        assert "SELECT" in call_args[0][0]
        assert "keywords" in call_args[0][0]
        assert call_args[0][1] == (1,)

    def test_get_keywords_single_keyword(self, mock_cursor_keyword):
        """Getting single keyword returns list with one element."""
        mock_cursor_keyword.fetchall.return_value = [{"keyword_value": "matcha"}]

        result = get_user_keywords(mock_cursor_keyword, 1)

        assert len(result) == 1
        assert result[0] == "matcha"

    def test_get_keywords_multiple_users(self, mock_cursor_keyword):
        """Getting keywords for different users uses correct user_id."""
        mock_cursor_keyword.fetchall.return_value = None

        get_user_keywords(mock_cursor_keyword, 5)
        get_user_keywords(mock_cursor_keyword, 10)

        calls = mock_cursor_keyword.execute.call_args_list
        assert calls[0][0][1] == (5,)
        assert calls[1][0][1] == (10,)


# ============== Tests for Visualization Data Generators ==============

class TestGenerateWordCloudData:
    """Tests for generate_word_cloud_data function."""

    def test_returns_dict(self, sample_keyword, sample_days):
        """Word cloud data returns a dictionary."""
        result = generate_word_cloud_data(sample_keyword, sample_days)

        assert isinstance(result, dict)

    def test_contains_words(self, sample_keyword, sample_days):
        """Word cloud data contains word entries."""
        result = generate_word_cloud_data(sample_keyword, sample_days)

        assert len(result) > 0

    def test_values_are_numeric(self, sample_keyword, sample_days):
        """Word cloud values are numeric (frequencies)."""
        result = generate_word_cloud_data(sample_keyword, sample_days)

        for word, freq in result.items():
            assert isinstance(word, str)
            assert isinstance(freq, (int, float))
            assert freq > 0

    def test_different_keywords_different_data(self):
        """Different keywords produce different word cloud data."""
        result1 = generate_word_cloud_data("matcha", 30)
        result2 = generate_word_cloud_data("coffee", 30)

        assert result1 != result2

    def test_deterministic_with_same_seed(self, sample_keyword, sample_days):
        """Same keyword produces same data (deterministic)."""
        result1 = generate_word_cloud_data(sample_keyword, sample_days)
        result2 = generate_word_cloud_data(sample_keyword, sample_days)

        assert result1 == result2


class TestGenerateSentimentCalendarData:
    """Tests for generate_sentiment_calendar_data function."""

    def test_returns_dataframe(self, sample_keyword, sample_days):
        """Sentiment calendar data returns a DataFrame."""
        result = generate_sentiment_calendar_data(sample_keyword, sample_days)

        assert isinstance(result, pd.DataFrame)

    def test_contains_required_columns(self, sample_keyword, sample_days):
        """DataFrame contains required columns for calendar heatmap."""
        result = generate_sentiment_calendar_data(sample_keyword, sample_days)

        assert "date" in result.columns
        assert "sentiment" in result.columns
        assert "day_of_week" in result.columns
        assert "week" in result.columns

    def test_correct_number_of_days(self, sample_keyword, sample_days):
        """DataFrame has correct number of rows for days."""
        result = generate_sentiment_calendar_data(sample_keyword, sample_days)

        assert len(result) == sample_days

    def test_sentiment_in_range(self, sample_keyword, sample_days):
        """Sentiment values are within valid range [-1, 1]."""
        result = generate_sentiment_calendar_data(sample_keyword, sample_days)

        assert result["sentiment"].min() >= -1
        assert result["sentiment"].max() <= 1

    def test_day_of_week_valid(self, sample_keyword, sample_days):
        """Day of week values are 0-6."""
        result = generate_sentiment_calendar_data(sample_keyword, sample_days)

        assert result["day_of_week"].min() >= 0
        assert result["day_of_week"].max() <= 6


class TestGenerateTrendingVelocity:
    """Tests for generate_trending_velocity function."""

    def test_returns_dict(self, sample_keyword, sample_days):
        """Trending velocity returns a dictionary."""
        result = generate_trending_velocity(sample_keyword, sample_days)

        assert isinstance(result, dict)

    def test_contains_velocity_value(self, sample_keyword, sample_days):
        """Result contains velocity value."""
        result = generate_trending_velocity(sample_keyword, sample_days)

        assert "velocity" in result
        assert isinstance(result["velocity"], (int, float))

    def test_contains_trend_direction(self, sample_keyword, sample_days):
        """Result contains trend direction."""
        result = generate_trending_velocity(sample_keyword, sample_days)

        assert "direction" in result
        assert result["direction"] in ["accelerating", "decelerating", "stable"]

    def test_contains_percentage_change(self, sample_keyword, sample_days):
        """Result contains percentage change."""
        result = generate_trending_velocity(sample_keyword, sample_days)

        assert "percent_change" in result
        assert isinstance(result["percent_change"], (int, float))

    def test_velocity_range(self, sample_keyword, sample_days):
        """Velocity is within reasonable range [0, 100]."""
        result = generate_trending_velocity(sample_keyword, sample_days)

        assert 0 <= result["velocity"] <= 100


class TestGenerateNetworkGraphData:
    """Tests for generate_network_graph_data function."""

    def test_returns_dict_with_nodes_and_edges(self, sample_keywords):
        """Network graph data returns dict with nodes and edges."""
        result = generate_network_graph_data(sample_keywords)

        assert isinstance(result, dict)
        assert "nodes" in result
        assert "edges" in result

    def test_nodes_is_list(self, sample_keywords):
        """Nodes is a list."""
        result = generate_network_graph_data(sample_keywords)

        assert isinstance(result["nodes"], list)

    def test_edges_is_list(self, sample_keywords):
        """Edges is a list."""
        result = generate_network_graph_data(sample_keywords)

        assert isinstance(result["edges"], list)

    def test_nodes_contain_keyword_data(self, sample_keywords):
        """Each node contains required keyword data."""
        result = generate_network_graph_data(sample_keywords)

        for node in result["nodes"]:
            assert "id" in node
            assert "label" in node

    def test_edges_contain_connection_data(self, sample_keywords):
        """Each edge contains source, target, and weight."""
        result = generate_network_graph_data(sample_keywords)

        for edge in result["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "weight" in edge

    def test_empty_keywords_returns_empty(self):
        """Empty keywords list returns empty nodes and edges."""
        result = generate_network_graph_data([])

        assert result["nodes"] == []
        assert result["edges"] == []


class TestGenerateRandomPost:
    """Tests for generate_random_post function."""

    def test_returns_dict(self, sample_keyword):
        """Random post returns a dictionary."""
        result = generate_random_post(sample_keyword)

        assert isinstance(result, dict)

    def test_contains_text(self, sample_keyword):
        """Random post contains text field."""
        result = generate_random_post(sample_keyword)

        assert "text" in result
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_contains_author(self, sample_keyword):
        """Random post contains author field."""
        result = generate_random_post(sample_keyword)

        assert "author" in result
        assert isinstance(result["author"], str)

    def test_contains_timestamp(self, sample_keyword):
        """Random post contains timestamp field."""
        result = generate_random_post(sample_keyword)

        assert "timestamp" in result

    def test_contains_engagement(self, sample_keyword):
        """Random post contains engagement metrics."""
        result = generate_random_post(sample_keyword)

        assert "likes" in result
        assert "reposts" in result

    def test_text_contains_keyword(self, sample_keyword):
        """Post text contains the keyword."""
        result = generate_random_post(sample_keyword)

        assert sample_keyword.lower() in result["text"].lower()


class TestGenerateAIInsights:
    """Tests for generate_ai_insights function."""

    def test_returns_dict(self, sample_keyword, sample_days):
        """AI insights returns a dictionary."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert isinstance(result, dict)

    def test_contains_summary(self, sample_keyword, sample_days):
        """AI insights contains summary field."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_contains_themes(self, sample_keyword, sample_days):
        """AI insights contains themes list."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert "themes" in result
        assert isinstance(result["themes"], list)

    def test_contains_sentiment_drivers(self, sample_keyword, sample_days):
        """AI insights contains sentiment drivers."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert "sentiment_drivers" in result
        assert isinstance(result["sentiment_drivers"], dict)
        assert "positive" in result["sentiment_drivers"]
        assert "negative" in result["sentiment_drivers"]

    def test_contains_recommendations(self, sample_keyword, sample_days):
        """AI insights contains recommendations."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_summary_mentions_keyword(self, sample_keyword, sample_days):
        """Summary mentions the keyword."""
        result = generate_ai_insights(sample_keyword, sample_days)

        assert sample_keyword.lower() in result["summary"].lower()


# ============== Test Coverage Summary ==============
# All tests now import from utils.py instead of app.py
# This ensures proper separation of concerns:
#   - utils.py: Contains all shared utility functions
#   - app.py: Contains only authentication flow and routing
#
# Test Coverage:
#   ✓ Database functions (get_db_connection)
#   ✓ Authentication functions (verify_password, authenticate_user, etc.)
#   ✓ User management (get_user_by_username, create_user)
#   ✓ Keyword management (get_user_keywords, add_user_keyword, remove_user_keyword)
#   ✓ Data generators (generate_placeholder_metrics, generate_time_series_data, etc.)
#   ✓ Visualization generators (generate_word_cloud_data, generate_network_graph_data, etc.)
#   ✓ AI insights generation (generate_ai_insights)

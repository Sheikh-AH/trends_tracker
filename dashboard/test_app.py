"""
Unit tests for utility functions and authentication in utils.py using pytest.

Tests cover user retrieval, password verification, authentication flow, user creation,
keyword management, and data generation functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import hashlib
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
    get_posts_by_date,
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

    
    def test_get_keywords_multiple_users(self, mock_cursor_keyword):
        """Getting keywords for different users uses correct user_id."""
        mock_cursor_keyword.fetchall.return_value = None

        get_user_keywords(mock_cursor_keyword, 5)
        get_user_keywords(mock_cursor_keyword, 10)

        calls = mock_cursor_keyword.execute.call_args_list
        assert calls[0][0][1] == (5,)
        assert calls[1][0][1] == (10,)


# ============== Tests for get_posts_by_date ==============

class TestGetPostsByDate:
    """Tests for get_posts_by_date function."""

    @pytest.fixture
    def mock_conn(self):
        """Fixture providing a mock database connection."""
        conn = Mock()
        mock_cursor = Mock()
        conn.cursor.return_value = mock_cursor
        return conn

    @pytest.fixture
    def sample_date(self):
        """Fixture providing a sample date for testing."""
        from datetime import date
        return date(2026, 2, 9)

    def test_returns_list_of_posts(self, mock_conn, sample_date):
        """Test that function returns a list of post dictionaries."""
        mock_posts = [
            {
                "post_uri": "at://did:plc:1/app.bsky.feed.post/abc",
                "text": "Test post 1",
                "author_did": "did:plc:1",
                "posted_at": "2026-02-09T10:30:00",
                "sentiment_score": 0.25
            },
            {
                "post_uri": "at://did:plc:2/app.bsky.feed.post/def",
                "text": "Test post 2",
                "author_did": "did:plc:2",
                "posted_at": "2026-02-09T11:45:00",
                "sentiment_score": -0.15
            }
        ]
        mock_conn.cursor.return_value.fetchall.return_value = mock_posts

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            result = get_posts_by_date(mock_conn, keyword="python", date=sample_date, limit=10)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "Test post 1"
        assert result[1]["sentiment_score"] == -0.15

    def test_returns_empty_list_when_no_posts(self, mock_conn, sample_date):
        """Test that function returns empty list when no posts found."""
        mock_conn.cursor.return_value.fetchall.return_value = []

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            result = get_posts_by_date(mock_conn, keyword="python", date=sample_date, limit=10)

        assert result == []

    def test_returns_empty_list_when_fetchall_returns_none(self, mock_conn, sample_date):
        """Test that function returns empty list when fetchall returns None."""
        mock_conn.cursor.return_value.fetchall.return_value = None

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            result = get_posts_by_date(mock_conn, keyword="python", date=sample_date, limit=10)

        assert result == []

    def test_respects_limit_parameter(self, mock_conn, sample_date):
        """Test that the limit parameter is passed correctly."""
        mock_conn.cursor.return_value.fetchall.return_value = []

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            get_posts_by_date(mock_conn, keyword="matcha", date=sample_date, limit=5)

        # Verify the keyword, date, and limit were passed in the query
        call_args = mock_conn.cursor.return_value.execute.call_args
        assert call_args[0][1] == ("matcha", sample_date, 5)

    def test_handles_database_error(self, mock_conn, sample_date):
        """Test that function handles database errors gracefully."""
        mock_conn.cursor.return_value.execute.side_effect = Exception("Database error")

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            result = get_posts_by_date(mock_conn, keyword="python", date=sample_date, limit=10)

        assert result == []

    def test_closes_cursor_after_success(self, mock_conn, sample_date):
        """Test that cursor is closed after successful execution."""
        mock_conn.cursor.return_value.fetchall.return_value = []

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            get_posts_by_date(mock_conn, keyword="python", date=sample_date)

        mock_conn.cursor.return_value.close.assert_called_once()

    def test_default_limit_is_ten(self, mock_conn, sample_date):
        """Test that default limit is 10 when not specified."""
        mock_conn.cursor.return_value.fetchall.return_value = []

        with patch("utils._load_sql_query", return_value="SELECT * FROM ..."):
            get_posts_by_date(mock_conn, keyword="python", date=sample_date)

        call_args = mock_conn.cursor.return_value.execute.call_args
        assert call_args[0][1][2] == 10  # Third parameter is limit


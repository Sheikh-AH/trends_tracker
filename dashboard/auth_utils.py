"""Authentication and user management utilities."""

"""NOTE:
hashlib — does the actual password hashing
secrets — generates a secure random salt
hmac — prevents timing attacks during comparison
"""

import hashlib
import hmac
import logging
import re
import secrets
from typing import Optional

import psycopg2
import streamlit as st

logger = logging.getLogger(__name__)


def get_user_by_username(cursor, email: str) -> Optional[dict]:
    """Retrieve user details from database by username."""
    query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    return result


def verify_password(stored_hash: str, entered_password: str) -> bool:
    """Verify if entered password matches the stored hash. Uses PBKDF2-SHA256 for password hashing."""
    parts = stored_hash.split("$")
    if len(parts) != 3:
        return False

    salt, iterations_str, stored_hash_hex = parts

    # Validate iterations is a valid integer
    if not iterations_str.isdigit():
        return False

    iterations = int(iterations_str)

    # Hash the entered password with the same salt
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        entered_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )

    # Compare hashes using time constant comparison to prevent timing attacks
    return hmac.compare_digest(hashed.hex(), stored_hash_hex)


def authenticate_user(cursor, username: str, password: str) -> bool:
    """Authenticate user by checking username and password."""
    user = get_user_by_username(cursor, username)

    if user is None:
        return False

    return verify_password(user["password_hash"], password)


def generate_password_hash(password: str, iterations: int = 100000) -> str:
    """Generate a password hash using PBKDF2-SHA256."""
    if not password:
        raise ValueError("Password cannot be empty")

    # Generate a random salt
    salt = secrets.token_hex(16)

    # Hash the password
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )

    # Return formatted hash
    return f"{salt}${iterations}${hashed.hex()}"


def validate_signup_input(email: str, password: str) -> bool:
    """Validate signup input: email format and password length."""
    if not email or not password:
        return False

    # Validate email format (basic check)
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return False

    # Validate password length
    if len(password) <= 8:
        return False

    return True


def create_user(cursor, email: str, password_hash: str) -> bool:
    """Insert a new user into the database."""
    try:
        query = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        cursor.execute(query, (email, password_hash))
        cursor.connection.commit()
        return True
    except psycopg2.IntegrityError:
        # Email already exists
        cursor.connection.rollback()
        st.error("Email already exists. Please use a different email.")
        return False
    except psycopg2.Error as e:
        logger.error(f"Database error creating user: {e}")
        st.error("Database error occurred. Please try again later.")
        cursor.connection.rollback()
        return False

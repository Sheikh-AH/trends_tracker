"""Keyword management utilities."""

import streamlit as st


@st.cache_data(ttl=3600)
def get_user_keywords(_cursor, user_id: int) -> list:
    """Retrieve all keywords for a user."""
    _cursor.execute(
        "SELECT k.keyword_value FROM keywords k JOIN user_keywords uk ON k.keyword_id = uk.keyword_id WHERE uk.user_id = %s ORDER BY k.keyword_value",
        (user_id,)
    )
    results = _cursor.fetchall()
    return [row["keyword_value"] for row in results] if results else []


def add_user_keyword(cursor, user_id: int, keyword: str) -> bool:
    """Add a keyword to a user's tracked keywords."""
    # Insert keyword into keywords table (case-insensitive, do nothing on conflict)
    cursor.execute(
        "INSERT INTO keywords (keyword_value) VALUES (LOWER(%s)) ON CONFLICT (keyword_value) DO NOTHING",
        (keyword,)
    )

    # Add entry to user_keywords table mapping user to keyword
    cursor.execute(
        "INSERT INTO user_keywords (user_id, keyword_id) SELECT %s, keyword_id FROM keywords WHERE LOWER(keyword_value) = LOWER(%s)",
        (user_id, keyword)
    )
    cursor.connection.commit()
    get_user_keywords.clear()
    return True


def remove_user_keyword(cursor, user_id: int, keyword: str) -> bool:
    """Remove a keyword from a user's tracked keywords."""
    cursor.execute(
        "DELETE FROM user_keywords WHERE user_id = %s AND keyword_id IN (SELECT keyword_id FROM keywords WHERE LOWER(keyword_value) = LOWER(%s))",
        (user_id, keyword)
    )
    cursor.connection.commit()
    get_user_keywords.clear()
    return True

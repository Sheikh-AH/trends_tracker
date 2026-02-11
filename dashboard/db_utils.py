"""Database connection and configuration utilities."""

import logging
import os
from typing import Optional

import psycopg2
import streamlit as st
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD")
}


@st.cache_resource
def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """Get persistent database connection for the entire session."""
    conn = psycopg2.connect(
        host=DB_CONFIG.get("host"),
        port=DB_CONFIG.get("port", 5432),
        database=DB_CONFIG.get("database"),
        user=DB_CONFIG.get("user"),
        password=DB_CONFIG.get("password")
    )
    logger.info("Database connection established.")
    return conn


@st.cache_resource
def get_db_connection_cleanup():
    """Register cleanup for database connection on app exit."""
    def close_conn():
        conn = get_db_connection()
        if conn:
            conn.close()
            logger.info("Database connection closed.")
    return close_conn

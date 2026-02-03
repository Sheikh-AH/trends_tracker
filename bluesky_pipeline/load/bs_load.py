"""Load BlueSky data into PostgreSQL database."""

from dotenv import load_dotenv
from os import environ as ENV, _Environ
import psycopg2


def get_db_connection(config: _Environ):
    """Establish a database connection using environment variables."""
    conn = psycopg2.connect(
        dbname=config.get("DB_NAME"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD"),
        host=config.get("DB_HOST"),
        port=config.get("DB_PORT", 5432)
    )
    return conn


if __name__ == "__main__":
    load_dotenv()
    conn = get_db_connection(ENV)
    pass

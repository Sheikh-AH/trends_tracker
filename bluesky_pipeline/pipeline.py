# pylint: disable=import-error
"""Main pipeline: Extract -> Transform -> Load."""

import sys
import logging
from pathlib import Path
from os import environ as ENV
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Add subdirectories to path
sys.path.insert(0, str(Path(__file__).parent / "extract"))
sys.path.insert(0, str(Path(__file__).parent / "transform"))
sys.path.insert(0, str(Path(__file__).parent / "load"))

from extract import stream_filtered_messages, get_keywords
from bs_transform import add_sentiment, add_uri
from bs_load import load_data, get_db_connection


if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    load_dotenv()
    conn = get_db_connection(ENV)

    
    def keyword_updater():
        """Function to get updated keywords from environment."""
        with conn.cursor() as cursor:
            return get_keywords(cursor, ENV)

    # 1. Extract: stream filtered messages from Bluesky (refreshes keywords every 60s)
    extracted = stream_filtered_messages(keyword_updater)
    logger.info("Completed extraction of messages.")
    # 2. Transform: add sentiment scores
    analyzer = SentimentIntensityAnalyzer()
    with_sentiment = add_sentiment(extracted, analyzer)
    logger.info("Completed sentiment analysis.")
    # 3. Transform: add post URIs
    with_uri = add_uri(with_sentiment)
    logger.info("Added URIs to posts.")
    # 4. Load posts
    load_data(conn, with_uri, batch_size=100)
    logger.info("Loaded data into database.")

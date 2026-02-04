# pylint: disable=import-error
"""Main pipeline: Extract -> Transform -> Load."""

import sys
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

    load_dotenv()

    # 1. Extract: stream filtered messages from Bluesky (refreshes keywords every 60s)
    extracted = stream_filtered_messages(lambda: get_keywords(ENV))

    # 2. Transform: add sentiment scores
    analyzer = SentimentIntensityAnalyzer()
    with_sentiment = add_sentiment(extracted, analyzer)

    # 3. Transform: add post URIs
    with_uri = add_uri(with_sentiment)

    # 4. Load posts
    conn = get_db_connection(ENV)
    load_data(conn, with_uri, batch_size=100)
    # for post in with_uri:
    #     print(post)

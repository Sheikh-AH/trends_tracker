"""Main pipeline: Extract -> Transform -> Load."""

from dotenv import load_dotenv
from os import environ as ENV

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from extract.extract import stream_filtered_messages
from transform.bs_transform import add_sentiment, add_uri
from load.bs_load import load_data


if __name__ == "__main__":
    load_dotenv()

    # Configuration
    keywords = {"cat", "dog", "trump"}  # Add your keywords here
    batch_size = 500

    # Initialize analyzer
    analyzer = SentimentIntensityAnalyzer()

    # Chain the pipeline: Extract -> Transform -> Load
    # 1. Extract: stream filtered messages from Bluesky
    extracted = stream_filtered_messages(keywords)

    # 2. Transform: add sentiment scores
    with_sentiment = add_sentiment(extracted, analyzer)

    # 3. Transform: add post URIs
    with_uri = add_uri(with_sentiment)

    # 4. Load: batch insert into database
    load_data(with_uri, batch_size)

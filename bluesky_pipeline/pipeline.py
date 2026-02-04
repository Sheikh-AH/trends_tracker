"""Main pipeline: Extract -> Transform -> Load."""

from dotenv import load_dotenv
from os import environ as ENV

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from extract.extract import stream_filtered_messages, get_keywords
from transform.bs_transform import add_sentiment, add_uri
from load.bs_load import load_data, get_db_connection

URI = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"


if __name__ == "__main__":

    load_dotenv()

    # Create a keyword fetcher that uses the current environment
    def keyword_fetcher():
        return get_keywords(ENV)

    # 1. Extract: stream filtered messages from Bluesky (refreshes keywords every 60s)
    extracted = stream_filtered_messages(keyword_fetcher, refresh_interval=60)

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

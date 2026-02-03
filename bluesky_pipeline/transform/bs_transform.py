"""Enriches extracted data with sentiment analysis."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def add_sentiment(stream, analyzer):
    """Add sentiment score to each post."""
    for post in stream:
        post["sentiment"] = analyzer.polarity_scores(post["text"])["compound"]
        yield post


def add_uri(stream):
    """Add a unique URI to each post based on author DID and rkey."""
    for post in stream:
        did = post.get("did", "")
        rkey = post.get("rkey", "")
        post["post_uri"] = f"at://{did}/app.bsky.feed.post/{rkey}"
        yield post


if __name__ == "__main__":
    # analyzer = SentimentIntensityAnalyzer()
    pass

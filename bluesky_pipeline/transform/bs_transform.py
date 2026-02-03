"""Enriches extracted data with sentiment analysis."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def add_sentiment(stream, analyzer):
    """Add sentiment score to each post."""
    for post in stream:
        post["sentiment"] = analyzer.polarity_scores(post["text"])["compound"]
        yield post


if __name__ == "__main__":
    # analyzer = SentimentIntensityAnalyzer()
    pass

"""Enriches extracted data with sentiment analysis."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()


def add_sentiment(stream, analyzer):
    """Add sentiment score to each post."""
    pass


if __name__ == "__main__":
    pass

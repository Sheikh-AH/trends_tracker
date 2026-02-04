from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from extract import stream_filtered_messages


def filter_posts(stream, keywords: set[str]):
    """Filter stream to only posts containing keywords."""
    for event in stream:
        if event.get("kind") != "commit":
            continue
        commit = event.get("commit", {})
        if commit.get("collection") != "app.bsky.feed.post":
            continue
        record = commit.get("record", {})
        text = record.get("text", "")
        text_lower = text.lower()
        matched_keywords = [kw for kw in keywords if kw in text_lower]
        if not matched_keywords:
            continue
        yield {
            "post_uri": f"at://{event.get('did')}/app.bsky.feed.post/{commit.get('rkey')}",
            "posted_at": record.get("createdAt"),
            "author_did": event.get("did"),
            "text": text,
            "keywords": matched_keywords,
            "reply_uri": record.get("reply", {}).get("parent", {}).get("uri"),
            "repost_uri": None,
        }


def add_sentiment(stream, analyzer):
    """Add sentiment score to each post."""
    for post in stream:
        post["sentiment"] = analyzer.polarity_scores(
            post['commit']['record']["text"])["compound"]
        yield post


def batch(stream, size: int):
    """Collect stream into batches."""
    buffer = []
    for item in stream:
        buffer.append(item)
        if len(buffer) >= size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer


def main():
    keywords = {"trump", "and", "biden",
                "election", "vaccine", "covid", "pandemic"}
    analyzer = SentimentIntensityAnalyzer()
    # Chain generators
    filtered = stream_filtered_messages(keywords)
    with_sentiment = add_sentiment(filtered, analyzer)
    for post in with_sentiment:
        print(post)

    # for b in batches:
    #     print(f"Batch of {len(b)} posts:")
    #     for post in b:
    #         print(f"  - {post['commit']['record']['text'][:50]}... (sentiment: {post['sentiment']:.2f})")


if __name__ == "__main__":
    main()

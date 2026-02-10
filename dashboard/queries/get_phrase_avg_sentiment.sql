SELECT
    AVG(b.sentiment_score::float) AS avg_sentiment,
    COUNT(*) AS post_count
FROM matches m
JOIN bluesky_posts b
    ON b.post_uri = m.post_uri
WHERE m.keyword_value = %s
    AND b.posted_at >= NOW() - INTERVAL %s
    AND b.text ILIKE %s
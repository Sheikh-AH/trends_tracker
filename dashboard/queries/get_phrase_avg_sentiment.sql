WITH limited_rows AS (
    SELECT b.sentiment_score
    FROM matches m
    JOIN bluesky_posts b
        ON b.post_uri = m.post_uri
    WHERE m.keyword_value = %s
        AND b.posted_at >= NOW() - INTERVAL %s
        AND b.text ILIKE %s
    LIMIT 500
)
SELECT
    AVG(sentiment_score::float) AS avg_sentiment
FROM limited_rows
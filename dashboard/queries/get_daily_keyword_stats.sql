SELECT
    DATE(bp.posted_at) AS date,
    COUNT(*) AS volume,
    COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL) AS replies,
    AVG(NULLIF(bp.sentiment_score, '')::float) AS avg_sentiment
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE LOWER(m.keyword_value) = LOWER(%s)
    AND bp.posted_at >= NOW() - INTERVAL '1 day' * %s
    AND bp.sentiment_score IS NOT NULL
GROUP BY DATE(bp.posted_at)
ORDER BY DATE(bp.posted_at);
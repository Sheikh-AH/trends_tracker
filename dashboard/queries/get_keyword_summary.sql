SELECT 
    DATE(bp.posted_at) as date,
    m.keyword_value as keyword,
    COUNT(*) as post_count,
    AVG(bp.sentiment_score::DECIMAL) as avg_sentiment
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE m.keyword_value = ANY(%s)
    AND bp.posted_at >= %s
GROUP BY DATE(bp.posted_at), m.keyword_value
ORDER BY date ASC;
SELECT 
    DATE(bp.posted_at) as date,
    AVG(CAST(bp.sentiment_score AS FLOAT)) as avg_sentiment,
    COUNT(*) as post_count
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE LOWER(m.keyword_value) = LOWER(%s)
  AND bp.posted_at >= NOW() - INTERVAL '%s days'
  AND bp.sentiment_score IS NOT NULL
  AND bp.sentiment_score != ''
GROUP BY DATE(bp.posted_at)
ORDER BY date ASC

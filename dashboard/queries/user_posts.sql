SELECT 
    k.keyword_value,
    COUNT(*) AS post_count,
    AVG(bp.sentiment_score::DECIMAL) AS avg_sentiment,
    SUM(CASE WHEN bp.reply_uri IS NULL AND bp.repost_uri IS NULL THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0) AS original_post_proportion,
    SUM(CASE WHEN bp.repost_uri IS NOT NULL THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0) AS repost_proportion,
    SUM(CASE WHEN bp.reply_uri IS NOT NULL THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0) AS reply_proportion,
    AVG(CASE WHEN bp.reply_uri IS NULL AND bp.repost_uri IS NULL THEN bp.sentiment_score::DECIMAL END) AS original_post_sentiment,
    AVG(CASE WHEN bp.repost_uri IS NOT NULL THEN bp.sentiment_score::DECIMAL END) AS repost_sentiment,
    AVG(CASE WHEN bp.reply_uri IS NOT NULL THEN bp.sentiment_score::DECIMAL END) AS reply_sentiment
FROM users u
JOIN user_keywords uk ON u.user_id = uk.user_id
JOIN keywords k ON uk.keyword_id = k.keyword_id
JOIN matches m ON k.keyword_value = m.keyword_value
JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
WHERE u.user_id = %s
  AND bp.posted_at >= CURRENT_DATE - INTERVAL '1 day'
  AND bp.posted_at < CURRENT_DATE
GROUP BY k.keyword_value
ORDER BY post_count DESC;
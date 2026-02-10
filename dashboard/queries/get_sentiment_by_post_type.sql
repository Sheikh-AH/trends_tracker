SELECT
    m.keyword_value,
    COUNT(*) AS post_count,
    COUNT(*) FILTER (WHERE bp.reply_uri IS NULL)::float 
        / NULLIF(COUNT(*), 0) AS original_post_proportion,
    COUNT(*) FILTER (WHERE bp.reply_uri IS NOT NULL)::float 
        / NULLIF(COUNT(*), 0) AS reply_proportion,
    AVG(NULLIF(bp.sentiment_score, '')::float) 
        FILTER (WHERE bp.reply_uri IS NULL) 
        AS original_post_sentiment,
    AVG(NULLIF(bp.sentiment_score, '')::float) 
        FILTER (WHERE bp.reply_uri IS NOT NULL) 
        AS reply_sentiment
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
JOIN keywords k ON m.keyword_value = k.keyword_value
join user_keywords uk ON k.keyword_id = uk.keyword_id
WHERE uk.user_id = %s
    AND bp.posted_at >= NOW() - INTERVAL '24 hours'
GROUP BY m.keyword_value
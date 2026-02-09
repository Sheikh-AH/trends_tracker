SELECT
    COUNT(CASE WHEN bp.posted_at >= %s THEN 1 END) as current_posts,
    COUNT(CASE WHEN bp.posted_at >= %s AND bp.posted_at < %s THEN 1 END) as baseline_posts,
    COUNT(CASE WHEN bp.posted_at >= %s AND repost_uri IS NOT NULL THEN 1 END) as current_reposts,
    COUNT(CASE WHEN bp.posted_at >= %s AND bp.posted_at < %s AND repost_uri IS NOT NULL THEN 1 END) as baseline_reposts,
    COUNT(CASE WHEN bp.posted_at >= %s AND reply_uri IS NOT NULL THEN 1 END) as current_comments,
    COUNT(CASE WHEN bp.posted_at >= %s AND bp.posted_at < %s AND reply_uri IS NOT NULL THEN 1 END) as baseline_comments,
    AVG(CASE WHEN bp.posted_at >= %s THEN CAST(sentiment_score AS FLOAT) END) as current_sentiment,
    AVG(CASE WHEN bp.posted_at >= %s AND bp.posted_at < %s THEN CAST(sentiment_score AS FLOAT) END) as baseline_sentiment
FROM bluesky_posts bp
WHERE EXISTS (
    SELECT 1 FROM matches m
    WHERE m.post_uri = bp.post_uri
    AND LOWER(m.keyword_value) = %s
)
AND bp.posted_at >= %s

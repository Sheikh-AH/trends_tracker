SELECT
    SUM(CASE WHEN bp.posted_at >= %s THEN 1 ELSE 0 END) as current_mentions,
    SUM(CASE WHEN bp.posted_at >= %s AND bp.posted_at < %s THEN 1 ELSE 0 END) as baseline_mentions
FROM matches m
JOIN bluesky_posts bp ON m.post_uri = bp.post_uri
WHERE LOWER(m.keyword_value) = %s
AND bp.posted_at >= %s

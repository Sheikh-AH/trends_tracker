SELECT bp.text
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE LOWER(m.keyword_value) = LOWER(%s)
  AND bp.posted_at >= NOW() - INTERVAL '%s days'
  AND bp.text IS NOT NULL
  AND bp.text != ''
ORDER BY bp.posted_at DESC
LIMIT %s

SELECT bp.post_uri, bp.text, bp.author_did, bp.posted_at, bp.sentiment_score
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE LOWER(m.keyword_value) = LOWER(%s)
  AND DATE(bp.posted_at) = %s
  AND bp.text IS NOT NULL
  AND bp.text != ''
ORDER BY RANDOM()
LIMIT %s

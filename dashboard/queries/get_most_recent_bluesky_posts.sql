SELECT bp.post_uri, bp.posted_at, bp.author_did, bp.text, bp.sentiment_score,
       bp.ingested_at, bp.reply_uri, bp.repost_uri
FROM bluesky_posts bp
JOIN matches m ON bp.post_uri = m.post_uri
WHERE LOWER(m.keyword_value) = LOWER(%s)
ORDER BY bp.posted_at DESC
LIMIT %s

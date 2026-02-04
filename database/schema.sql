-- Users table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    send_alert BOOLEAN DEFAULT TRUE,
    send_email BOOLEAN DEFAULT TRUE
);

-- Keywords table
CREATE TABLE keywords (
    keyword_id SMALLSERIAL PRIMARY KEY,
    keyword_value VARCHAR(255) NOT NULL UNIQUE
);

-- User keywords junction table
CREATE TABLE user_keywords (
    user_keyword_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    keyword_id BIGINT REFERENCES keywords(keyword_id) ON DELETE CASCADE
);

-- BlueSky posts table
CREATE TABLE bluesky_posts (
    post_uri VARCHAR(255) PRIMARY KEY,
    posted_at TIMESTAMP,
    author_did VARCHAR(255),
    text TEXT,
    sentiment_score VARCHAR(50),
    ingested_at TIMESTAMP DEFAULT NOW(),
    reply_uri VARCHAR(255),
    repost_uri VARCHAR(255)
);

-- Matches table
CREATE TABLE matches (
    match_id BIGSERIAL PRIMARY KEY,
    post_uri VARCHAR(255) REFERENCES bluesky_posts(post_uri) ON DELETE CASCADE,
    keyword_value VARCHAR(255) REFERENCES keywords(keyword_value) ON DELETE CASCADE
);

-- Google trends table
CREATE TABLE google_trends (
    trend_id BIGSERIAL PRIMARY KEY,
    keyword_value VARCHAR(255) REFERENCES keywords(keyword_value) ON DELETE CASCADE,
    search_volume BIGINT,
    trend_date TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW()
);

-- LLM summary table
CREATE TABLE llm_summary (
    summary_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    summary TEXT
);
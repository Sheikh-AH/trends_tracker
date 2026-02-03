-- Users table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    send_alert BOOLEAN DEFAULT TRUE,
    send_email BOOLEAN DEFAULT TRUE
);

-- User topics table
CREATE TABLE user_topics (
    topic_id SMALLSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    topic_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Keywords table
CREATE TABLE keywords (
    keyword_id SMALLSERIAL PRIMARY KEY,
    topic_id BIGINT REFERENCES user_topics(topic_id) ON DELETE CASCADE,
    keyword_name VARCHAR(255) NOT NULL
);

-- BlueSky posts table
CREATE TABLE bluesky_posts (
    post_uri VARCHAR(255) PRIMARY KEY,
    posted_at TIMESTAMP,
    author_did VARCHAR(255),
    text TEXT,
    matched_keyword VARCHAR(255),
    sentiment_score DECIMAL(4,3),
    ingested_at TIMESTAMP DEFAULT NOW(),
    reply_uri VARCHAR(255),
    repost_uri VARCHAR(255)
);

-- Google trends table
CREATE TABLE google_trends (
    id BIGSERIAL PRIMARY KEY,
    keyword VARCHAR(255),
    search_volume BIGINT,
    trend_date DATE,
    ingested_at TIMESTAMP DEFAULT NOW()
);

-- LLM summary table
CREATE TABLE llm_summary (
    id BIGSERIAL PRIMARY KEY,
    keyword VARCHAR(255),
    daily_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
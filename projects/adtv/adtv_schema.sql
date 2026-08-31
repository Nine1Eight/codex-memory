-- =====================================================
-- ADTV PRODUCTION SCHEMA
-- =====================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255),
    wallet_address VARCHAR(255) UNIQUE,
    user_tier VARCHAR(50) DEFAULT 'base',
    current_cu_balance DECIMAL(18,6) DEFAULT 0,
    lifetime_cu DECIMAL(18,6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ADVERTISERS
CREATE TABLE advertisers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CREATIVES
CREATE TABLE creatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advertiser_id UUID REFERENCES advertisers(id) ON DELETE CASCADE,
    media_url TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    cpv DECIMAL(10,4) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- BLOCKS (SESSION-SCOPED)
CREATE TABLE blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    total_cpv DECIMAL(12,4) NOT NULL DEFAULT 0,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- BLOCK ADS
CREATE TABLE block_ads (
    block_id UUID REFERENCES blocks(id) ON DELETE CASCADE,
    creative_id UUID REFERENCES creatives(id) ON DELETE CASCADE,
    position INTEGER CHECK (position BETWEEN 1 AND 5),
    PRIMARY KEY (block_id, position)
);

-- QUESTION TRACKING
CREATE TABLE question_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creative_id UUID REFERENCES creatives(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seen_questions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    question_variant_id UUID REFERENCES question_variants(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, question_variant_id)
);

-- CU TRANSACTIONS
CREATE TABLE cu_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    block_id UUID REFERENCES blocks(id) ON DELETE CASCADE,
    cu_amount DECIMAL(18,6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- REVENUE EVENTS
CREATE TABLE revenue_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id UUID REFERENCES blocks(id) ON DELETE CASCADE,
    advertiser_id UUID REFERENCES advertisers(id) ON DELETE SET NULL,
    cpv DECIMAL(12,4) NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DAILY POOLS
CREATE TABLE daily_revenue_pools (
    pool_date DATE PRIMARY KEY,
    total_revenue DECIMAL(18,4),
    platform_share DECIMAL(18,4),
    user_pool DECIMAL(18,4),
    total_cu DECIMAL(18,6),
    cu_rate DECIMAL(18,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- USER SETTLEMENTS
CREATE TABLE user_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_date DATE REFERENCES daily_revenue_pools(pool_date) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    cu_earned DECIMAL(18,6) NOT NULL,
    usd_allocated DECIMAL(18,6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_user_settlements_pool_user ON user_settlements(pool_date, user_id);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_blocks_user ON blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_cu_user ON cu_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_revenue_verified ON revenue_events(verified);

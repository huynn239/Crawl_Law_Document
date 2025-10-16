-- TNPL Database Schema
-- Thuật ngữ pháp lý (Legal Terms)

-- Table: tnpl_terms
CREATE TABLE IF NOT EXISTS tnpl_terms (
    term_id SERIAL PRIMARY KEY,
    term_name VARCHAR(500) NOT NULL,
    definition TEXT,
    url VARCHAR(1000) UNIQUE NOT NULL,
    source_crawl VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table: tnpl_crawl_sessions
CREATE TABLE IF NOT EXISTS tnpl_crawl_sessions (
    session_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_terms INTEGER DEFAULT 0,
    new_terms INTEGER DEFAULT 0,
    updated_terms INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'RUNNING',
    notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_name ON tnpl_terms(term_name);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_created ON tnpl_terms(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_search ON tnpl_terms USING gin(to_tsvector('english', term_name || ' ' || COALESCE(definition, '')));

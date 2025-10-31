-- Tạo bảng crawl_sessions
CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'RUNNING',
    total_docs INTEGER DEFAULT 0,
    new_versions INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0
);

-- Thêm cột session_id vào document_versions
ALTER TABLE document_versions 
ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES crawl_sessions(session_id);

-- Xóa bảng cũ (nếu có)
DROP TABLE IF EXISTS documents_snapshots;
DROP TABLE IF EXISTS crawl_snapshots;

-- Thêm cột download_link vào documents_finals
ALTER TABLE documents_finals 
ADD COLUMN IF NOT EXISTS download_link TEXT;

-- Tạo index
CREATE INDEX IF NOT EXISTS idx_versions_session ON document_versions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON crawl_sessions(started_at);

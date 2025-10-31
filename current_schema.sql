-- Schema hiện tại cho Thư viện pháp luật crawler
-- Export từ Supabase để migrate sang DB công ty

-- 1. Bảng doc_urls - Danh sách URL cần crawl
CREATE TABLE doc_urls (
    url TEXT PRIMARY KEY,
    doc_id TEXT,
    title TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    last_update_date DATE,
    last_attempt_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doc_urls_status ON doc_urls(status);
CREATE INDEX idx_doc_urls_priority ON doc_urls(priority DESC);
CREATE INDEX idx_doc_urls_doc_id ON doc_urls(doc_id);

-- 2. Bảng documents_finals - Văn bản cuối cùng (latest version)
CREATE TABLE documents_finals (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    hash TEXT NOT NULL,
    update_date DATE,
    metadata JSONB,
    download_link TEXT,
    relations_summary JSONB,
    last_crawled TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_finals_hash ON documents_finals(hash);
CREATE INDEX idx_documents_finals_update_date ON documents_finals(update_date);
CREATE INDEX idx_documents_finals_metadata ON documents_finals USING GIN(metadata);

-- 3. Bảng document_versions - Lịch sử versions
CREATE TABLE document_versions (
    version_id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    content JSONB NOT NULL,
    session_id INTEGER,
    diff_summary JSONB,
    source_snapshot_date DATE,
    crawled_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_document_versions_doc_id ON document_versions(doc_id);
CREATE INDEX idx_document_versions_session ON document_versions(session_id);
CREATE INDEX idx_document_versions_crawled ON document_versions(crawled_at DESC);

-- 4. Bảng document_relations - Quan hệ giữa văn bản
CREATE TABLE document_relations (
    relation_id BIGSERIAL PRIMARY KEY,
    source_doc_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_doc_id TEXT,
    target_url TEXT NOT NULL,
    target_title TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_document_relations_source ON document_relations(source_doc_id);
CREATE INDEX idx_document_relations_target ON document_relations(target_doc_id);
CREATE INDEX idx_document_relations_type ON document_relations(relation_type);
CREATE INDEX idx_document_relations_resolved ON document_relations(resolved);

-- 5. Bảng document_files - Files đính kèm
CREATE TABLE document_files (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_url TEXT NOT NULL,
    download_status TEXT DEFAULT 'pending' CHECK (download_status IN ('pending', 'downloaded', 'failed')),
    local_path TEXT,
    downloaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_document_files_doc_id ON document_files(doc_id);
CREATE INDEX idx_document_files_status ON document_files(download_status);
CREATE INDEX idx_document_files_type ON document_files(file_type);

-- 6. Bảng crawl_sessions - Tracking crawl sessions
CREATE TABLE crawl_sessions (
    session_id SERIAL PRIMARY KEY,
    status TEXT DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_docs INTEGER DEFAULT 0,
    new_versions INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0
);

CREATE INDEX idx_crawl_sessions_status ON crawl_sessions(status);
CREATE INDEX idx_crawl_sessions_started ON crawl_sessions(started_at DESC);

-- Foreign keys
ALTER TABLE document_versions ADD CONSTRAINT fk_versions_session 
    FOREIGN KEY (session_id) REFERENCES crawl_sessions(session_id) ON DELETE SET NULL;

-- Comments
COMMENT ON TABLE doc_urls IS 'Danh sách URL cần crawl với status tracking';
COMMENT ON TABLE documents_finals IS 'Văn bản cuối cùng (latest version only)';
COMMENT ON TABLE document_versions IS 'Lịch sử tất cả versions của văn bản';
COMMENT ON TABLE document_relations IS 'Quan hệ giữa các văn bản (tab4)';
COMMENT ON TABLE document_files IS 'Files đính kèm (tab8)';
COMMENT ON TABLE crawl_sessions IS 'Tracking các lần crawl';

-- ============================================================
-- SUPABASE SCHEMA FINAL
-- Cấu trúc đơn giản, giữ tên bảng như v2
-- ============================================================

-- ============================================================
-- 1. CREATE SCHEMAS
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tvpl;
CREATE SCHEMA IF NOT EXISTS tnpl;
CREATE SCHEMA IF NOT EXISTS system;

COMMENT ON SCHEMA tvpl IS 'Văn bản pháp luật';
COMMENT ON SCHEMA tnpl IS 'Thuật ngữ pháp lý';
COMMENT ON SCHEMA system IS 'System tables';

-- ============================================================
-- 2. TVPL SCHEMA
-- ============================================================

-- 2.1. document_finals (Văn bản hiện tại)
CREATE TABLE tvpl.document_finals (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    update_date DATE,
    effective_date DATE,
    expire_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    download_link TEXT,
    relations_summary JSONB,
    last_crawled TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.2. document_relations (Quan hệ văn bản)
CREATE TABLE tvpl.document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id TEXT NOT NULL REFERENCES tvpl.document_finals(doc_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    target_doc_id TEXT,
    target_url TEXT,
    target_title TEXT,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.3. document_files (File đính kèm)
CREATE TABLE tvpl.document_files (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES tvpl.document_finals(doc_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_url TEXT NOT NULL,
    file_size BIGINT,
    local_path TEXT,
    download_status TEXT DEFAULT 'pending',
    downloaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.4. document_versions (Lịch sử thay đổi)
CREATE TABLE tvpl.document_versions (
    version_id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES tvpl.document_finals(doc_id) ON DELETE CASCADE,
    version_hash TEXT NOT NULL,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    content JSONB,
    diff_summary JSONB,
    source_snapshot_date DATE,
    session_id BIGINT
);

-- ============================================================
-- 3. TNPL SCHEMA
-- ============================================================

-- 3.1. terms (Thuật ngữ pháp lý)
CREATE TABLE tnpl.terms (
    term_id SERIAL PRIMARY KEY,
    term_name VARCHAR(500) NOT NULL,
    definition TEXT,
    url VARCHAR(1000) UNIQUE NOT NULL,
    source_crawl VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.2. crawl_sessions (Phiên crawl TNPL)
CREATE TABLE tnpl.crawl_sessions (
    session_id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_terms INTEGER DEFAULT 0,
    new_terms INTEGER DEFAULT 0,
    updated_terms INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'RUNNING',
    notes TEXT
);

-- ============================================================
-- 4. SYSTEM SCHEMA
-- ============================================================

-- 4.1. crawl_sessions (Phiên crawl TVPL)
CREATE TABLE system.crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_docs INTEGER DEFAULT 0,
    new_versions INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0
);

-- 4.2. crawl_url (Hàng đợi URL cần crawl)
CREATE TABLE system.crawl_url (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    doc_id TEXT,
    title TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT
);

-- 4.3. audit_logs (Nhật ký thay đổi)
CREATE TABLE system.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    changed_by TEXT,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. INDEXES
-- ============================================================

-- TVPL indexes
CREATE INDEX idx_tvpl_document_finals_hash ON tvpl.document_finals(hash);
CREATE INDEX idx_tvpl_document_finals_last_crawled ON tvpl.document_finals(last_crawled DESC);
CREATE INDEX idx_tvpl_document_relations_source ON tvpl.document_relations(source_doc_id);
CREATE INDEX idx_tvpl_document_relations_target ON tvpl.document_relations(target_doc_id);
CREATE INDEX idx_tvpl_document_files_doc_id ON tvpl.document_files(doc_id);
CREATE INDEX idx_tvpl_document_files_status ON tvpl.document_files(download_status);
CREATE INDEX idx_tvpl_document_versions_doc_id ON tvpl.document_versions(doc_id);
CREATE INDEX idx_tvpl_document_versions_session ON tvpl.document_versions(session_id);

-- TNPL indexes
CREATE INDEX idx_tnpl_terms_name ON tnpl.terms(term_name);
CREATE INDEX idx_tnpl_terms_created ON tnpl.terms(created_at DESC);

-- System indexes
CREATE INDEX idx_system_crawl_sessions_status ON system.crawl_sessions(status);
CREATE INDEX idx_system_crawl_url_status ON system.crawl_url(status);
CREATE INDEX idx_system_crawl_url_priority ON system.crawl_url(priority DESC, added_at ASC);
CREATE INDEX idx_system_audit_entity ON system.audit_logs(entity_type, entity_id);

-- ============================================================
-- 6. VIEWS (Public schema)
-- ============================================================

-- 6.1. v_documents_overview
CREATE OR REPLACE VIEW public.v_documents_overview AS
SELECT 
    d.doc_id,
    d.title,
    d.url,
    d.update_date,
    d.is_active,
    d.last_crawled,
    COUNT(DISTINCT r.id) AS total_relations,
    COUNT(DISTINCT f.id) AS total_files,
    COUNT(DISTINCT CASE WHEN f.download_status = 'downloaded' THEN f.id END) AS downloaded_files
FROM tvpl.document_finals d
LEFT JOIN tvpl.document_relations r ON d.doc_id = r.source_doc_id
LEFT JOIN tvpl.document_files f ON d.doc_id = f.doc_id
GROUP BY d.doc_id, d.title, d.url, d.update_date, d.is_active, d.last_crawled;

-- 6.2. v_pending_downloads
CREATE OR REPLACE VIEW public.v_pending_downloads AS
SELECT 
    f.id,
    f.doc_id,
    d.title AS doc_title,
    f.file_name,
    f.file_type,
    f.file_url,
    f.download_status,
    f.created_at
FROM tvpl.document_files f
JOIN tvpl.document_finals d ON f.doc_id = d.doc_id
WHERE f.download_status IN ('pending', 'failed')
ORDER BY f.created_at ASC;

-- 6.3. v_tnpl_terms
CREATE OR REPLACE VIEW public.v_tnpl_terms AS
SELECT 
    term_id,
    term_name,
    LEFT(definition, 200) AS definition_preview,
    url,
    created_at
FROM tnpl.terms
ORDER BY created_at DESC;

-- 6.4. v_document_relations
CREATE OR REPLACE VIEW public.v_document_relations AS
SELECT 
    r.id,
    r.source_doc_id,
    d_source.title AS source_title,
    r.relation_type,
    r.target_doc_id,
    r.target_title,
    r.target_url,
    d_target.title AS target_title_resolved,
    r.resolved,
    CASE 
        WHEN d_target.doc_id IS NOT NULL THEN 'crawled'
        ELSE 'pending'
    END AS target_status
FROM tvpl.document_relations r
JOIN tvpl.document_finals d_source ON r.source_doc_id = d_source.doc_id
LEFT JOIN tvpl.document_finals d_target ON r.target_doc_id = d_target.doc_id;

-- ============================================================
-- 7. GRANT PERMISSIONS
-- ============================================================

GRANT USAGE ON SCHEMA tvpl TO anon, authenticated;
GRANT USAGE ON SCHEMA tnpl TO anon, authenticated;
GRANT USAGE ON SCHEMA system TO authenticated;

GRANT SELECT ON ALL TABLES IN SCHEMA tvpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA tnpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA system TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;

-- ============================================================
-- 8. COMMENTS
-- ============================================================

COMMENT ON TABLE tvpl.document_finals IS 'Văn bản pháp luật hiện tại';
COMMENT ON TABLE tvpl.document_relations IS 'Quan hệ giữa các văn bản';
COMMENT ON TABLE tvpl.document_files IS 'File đính kèm văn bản';
COMMENT ON TABLE tvpl.document_versions IS 'Lịch sử thay đổi văn bản';
COMMENT ON TABLE tnpl.terms IS 'Thuật ngữ pháp lý';
COMMENT ON TABLE tnpl.crawl_sessions IS 'Phiên crawl thuật ngữ';
COMMENT ON TABLE system.crawl_sessions IS 'Phiên crawl văn bản';
COMMENT ON TABLE system.crawl_url IS 'Hàng đợi URL cần crawl';
COMMENT ON TABLE system.audit_logs IS 'Nhật ký thay đổi dữ liệu';

-- ============================================================
-- SUPABASE SCHEMA WITH NAMESPACES
-- Sử dụng PostgreSQL schemas để tổ chức data
-- ============================================================

-- ============================================================
-- 1. TẠO SCHEMAS (Namespaces)
-- ============================================================

-- Schema cho văn bản pháp luật
CREATE SCHEMA IF NOT EXISTS tvpl;

-- Schema cho thuật ngữ pháp lý
CREATE SCHEMA IF NOT EXISTS tnpl;

-- Schema cho system/admin
CREATE SCHEMA IF NOT EXISTS system;

COMMENT ON SCHEMA tvpl IS 'Thư viện pháp luật - Documents, Relations, Files';
COMMENT ON SCHEMA tnpl IS 'Thuật ngữ pháp lý - Legal Terms';
COMMENT ON SCHEMA system IS 'System tables - Crawl sessions, Audit logs';

-- ============================================================
-- 2. TVPL SCHEMA (Văn bản pháp luật)
-- ============================================================

-- 2.1. Documents
CREATE TABLE tvpl.documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    issue_date DATE,
    effective_date DATE,
    expire_date DATE,
    update_date DATE,
    is_active BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'active',
    content_hash TEXT NOT NULL,
    last_crawled_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.2. Document Metadata
CREATE TABLE tvpl.document_metadata (
    doc_id TEXT PRIMARY KEY REFERENCES tvpl.documents(doc_id) ON DELETE CASCADE,
    so_hieu TEXT,
    loai_van_ban TEXT,
    linh_vuc TEXT,
    co_quan_ban_hanh TEXT,
    nguoi_ky TEXT,
    trich_yeu TEXT,
    noi_dung_tom_tat TEXT,
    extra_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.3. Document Relations
CREATE TABLE tvpl.document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id TEXT NOT NULL REFERENCES tvpl.documents(doc_id) ON DELETE CASCADE,
    target_doc_id TEXT REFERENCES tvpl.documents(doc_id) ON DELETE SET NULL,
    relation_type TEXT NOT NULL,
    target_url TEXT,
    target_title TEXT,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_doc_id, relation_type, target_url)
);

-- 2.4. Document Files
CREATE TABLE tvpl.document_files (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES tvpl.documents(doc_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size BIGINT,
    storage_bucket TEXT,
    storage_path TEXT,
    download_status TEXT DEFAULT 'pending',
    download_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    downloaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(doc_id, file_url)
);

-- 2.5. Document Versions
CREATE TABLE tvpl.document_versions (
    version_id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES tvpl.documents(doc_id) ON DELETE CASCADE,
    session_id BIGINT,
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    changed_fields TEXT[],
    relations_added INTEGER DEFAULT 0,
    relations_removed INTEGER DEFAULT 0,
    content_snapshot JSONB,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    source_update_date DATE,
    UNIQUE(doc_id, version_number)
);

-- ============================================================
-- 3. TNPL SCHEMA (Thuật ngữ pháp lý)
-- ============================================================

-- 3.1. Terms
CREATE TABLE tnpl.terms (
    term_id SERIAL PRIMARY KEY,
    term_name VARCHAR(500) NOT NULL,
    definition TEXT,
    url VARCHAR(1000) UNIQUE NOT NULL,
    source_crawl VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.2. Crawl Sessions (cho TNPL)
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
-- 4. SYSTEM SCHEMA (System tables)
-- ============================================================

-- 4.1. Crawl Sessions (cho TVPL)
CREATE TABLE system.crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    session_type TEXT DEFAULT 'manual',
    started_by TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    total_docs INTEGER DEFAULT 0,
    new_docs INTEGER DEFAULT 0,
    updated_docs INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0,
    failed_docs INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    notes TEXT
);

-- 4.2. Crawl Queue
CREATE TABLE system.crawl_queue (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    doc_id TEXT,
    title TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 4.3. Audit Logs
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
CREATE INDEX idx_tvpl_documents_status ON tvpl.documents(status);
CREATE INDEX idx_tvpl_documents_last_crawled ON tvpl.documents(last_crawled_at DESC);
CREATE INDEX idx_tvpl_metadata_so_hieu ON tvpl.document_metadata(so_hieu);
CREATE INDEX idx_tvpl_relations_source ON tvpl.document_relations(source_doc_id);
CREATE INDEX idx_tvpl_relations_target ON tvpl.document_relations(target_doc_id);
CREATE INDEX idx_tvpl_files_doc_id ON tvpl.document_files(doc_id);
CREATE INDEX idx_tvpl_files_status ON tvpl.document_files(download_status);
CREATE INDEX idx_tvpl_versions_doc_id ON tvpl.document_versions(doc_id);

-- TNPL indexes
CREATE INDEX idx_tnpl_terms_name ON tnpl.terms(term_name);
CREATE INDEX idx_tnpl_terms_created ON tnpl.terms(created_at DESC);

-- System indexes
CREATE INDEX idx_system_sessions_status ON system.crawl_sessions(status);
CREATE INDEX idx_system_queue_status ON system.crawl_queue(status);
CREATE INDEX idx_system_queue_priority ON system.crawl_queue(priority DESC, added_at ASC);
CREATE INDEX idx_system_audit_entity ON system.audit_logs(entity_type, entity_id);

-- ============================================================
-- 6. VIEWS (Trong public schema để dễ truy cập)
-- ============================================================

-- 6.1. Document Overview (cross-schema view)
CREATE OR REPLACE VIEW public.v_documents_overview AS
SELECT 
    d.doc_id,
    d.title,
    d.url,
    m.so_hieu,
    m.loai_van_ban,
    m.co_quan_ban_hanh,
    d.issue_date,
    d.status,
    d.last_crawled_at,
    COUNT(DISTINCT r.id) AS total_relations,
    COUNT(DISTINCT f.id) AS total_files,
    COUNT(DISTINCT CASE WHEN f.download_status = 'completed' THEN f.id END) AS downloaded_files
FROM tvpl.documents d
LEFT JOIN tvpl.document_metadata m ON d.doc_id = m.doc_id
LEFT JOIN tvpl.document_relations r ON d.doc_id = r.source_doc_id
LEFT JOIN tvpl.document_files f ON d.doc_id = f.doc_id
GROUP BY d.doc_id, d.title, d.url, m.so_hieu, m.loai_van_ban, m.co_quan_ban_hanh, 
         d.issue_date, d.status, d.last_crawled_at;

-- 6.2. Pending Downloads
CREATE OR REPLACE VIEW public.v_pending_downloads AS
SELECT 
    f.id,
    f.doc_id,
    d.title AS doc_title,
    f.file_name,
    f.file_type,
    f.file_url,
    f.download_status,
    f.download_attempts,
    f.created_at
FROM tvpl.document_files f
JOIN tvpl.documents d ON f.doc_id = d.doc_id
WHERE f.download_status IN ('pending', 'failed')
ORDER BY f.download_attempts ASC, f.created_at ASC;

-- 6.3. TNPL Terms Overview
CREATE OR REPLACE VIEW public.v_tnpl_terms AS
SELECT 
    term_id,
    term_name,
    LEFT(definition, 200) AS definition_preview,
    url,
    created_at
FROM tnpl.terms
ORDER BY created_at DESC;

-- ============================================================
-- 7. GRANT PERMISSIONS (cho anon & authenticated roles)
-- ============================================================

-- Grant usage on schemas
GRANT USAGE ON SCHEMA tvpl TO anon, authenticated;
GRANT USAGE ON SCHEMA tnpl TO anon, authenticated;
GRANT USAGE ON SCHEMA system TO authenticated; -- Chỉ authenticated mới thấy system

-- Grant select on tables (read-only cho anon)
GRANT SELECT ON ALL TABLES IN SCHEMA tvpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA tnpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA system TO authenticated;

-- Grant all on views
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;

-- ============================================================
-- 8. RLS POLICIES (Row Level Security)
-- ============================================================

-- Enable RLS on sensitive tables
ALTER TABLE system.audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Chỉ service_role mới thấy audit logs
CREATE POLICY "Service role only" ON system.audit_logs
    FOR ALL TO service_role
    USING (true);

-- ============================================================
-- 9. ADDITIONAL VIEWS
-- ============================================================

-- 9.1. Document Relations Detail
CREATE OR REPLACE VIEW public.v_document_relations AS
SELECT 
    r.id,
    r.source_doc_id,
    d_source.title AS source_title,
    m_source.so_hieu AS source_so_hieu,
    r.relation_type,
    r.target_doc_id,
    r.target_title,
    r.target_url,
    d_target.title AS target_title_resolved,
    m_target.so_hieu AS target_so_hieu,
    r.is_resolved,
    CASE 
        WHEN d_target.doc_id IS NOT NULL THEN 'crawled'
        ELSE 'pending'
    END AS target_status
FROM tvpl.document_relations r
JOIN tvpl.documents d_source ON r.source_doc_id = d_source.doc_id
LEFT JOIN tvpl.document_metadata m_source ON d_source.doc_id = m_source.doc_id
LEFT JOIN tvpl.documents d_target ON r.target_doc_id = d_target.doc_id
LEFT JOIN tvpl.document_metadata m_target ON d_target.doc_id = m_target.doc_id;

-- 9.2. Document Full Info
CREATE OR REPLACE VIEW public.v_document_full AS
SELECT 
    d.doc_id,
    d.title,
    d.url,
    d.issue_date,
    d.effective_date,
    d.status,
    m.so_hieu,
    m.loai_van_ban,
    m.co_quan_ban_hanh,
    m.trich_yeu,
    COUNT(DISTINCT r.id) AS total_relations,
    COUNT(DISTINCT f.id) AS total_files,
    COUNT(DISTINCT CASE WHEN f.download_status = 'completed' THEN f.id END) AS downloaded_files
FROM tvpl.documents d
LEFT JOIN tvpl.document_metadata m ON d.doc_id = m.doc_id
LEFT JOIN tvpl.document_relations r ON d.doc_id = r.source_doc_id
LEFT JOIN tvpl.document_files f ON d.doc_id = f.doc_id
GROUP BY d.doc_id, d.title, d.url, d.issue_date, d.effective_date, d.status,
         m.so_hieu, m.loai_van_ban, m.co_quan_ban_hanh, m.trich_yeu;

-- 9.3. Unresolved Relations
CREATE OR REPLACE VIEW public.v_unresolved_relations AS
SELECT 
    r.target_url,
    r.target_title,
    COUNT(*) AS reference_count,
    STRING_AGG(DISTINCT r.source_doc_id, ', ') AS referenced_by_docs
FROM tvpl.document_relations r
WHERE r.is_resolved = false
GROUP BY r.target_url, r.target_title
ORDER BY reference_count DESC;

-- ============================================================
-- 10. COMMENTS
-- ============================================================

COMMENT ON TABLE tvpl.documents IS 'Văn bản pháp luật';
COMMENT ON TABLE tvpl.document_metadata IS 'Metadata chi tiết văn bản';
COMMENT ON TABLE tvpl.document_relations IS 'Quan hệ giữa các văn bản';
COMMENT ON TABLE tvpl.document_files IS 'File đính kèm';
COMMENT ON TABLE tnpl.terms IS 'Thuật ngữ pháp lý';
COMMENT ON TABLE system.crawl_sessions IS 'Phiên crawl';
COMMENT ON TABLE system.crawl_queue IS 'Hàng đợi crawl';
COMMENT ON TABLE system.audit_logs IS 'Nhật ký thay đổi';

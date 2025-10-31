-- Schema Supabase giống PostgreSQL local (tvpl_crawl)

-- 1. Bảng crawl_sessions
CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_docs INTEGER DEFAULT 0,
    new_versions INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0
);

-- 2. Bảng doc_urls (danh sách URL cần crawl)
CREATE TABLE IF NOT EXISTS doc_urls (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    doc_id TEXT,
    title TEXT,
    status TEXT DEFAULT 'pending', -- pending, crawling, completed, failed
    priority INTEGER DEFAULT 0,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT
);

-- 3. Bảng documents_finals (văn bản hiện tại)
CREATE TABLE IF NOT EXISTS documents_finals (
    doc_id TEXT NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
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

-- 4. Bảng document_versions (lịch sử thay đổi)
CREATE TABLE IF NOT EXISTS document_versions (
    version_id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    content JSONB,
    diff_summary JSONB,
    source_snapshot_date DATE,
    session_id BIGINT REFERENCES crawl_sessions(session_id)
);

-- 5. Bảng document_relations (quan hệ văn bản)
CREATE TABLE IF NOT EXISTS document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_doc_id TEXT,
    target_url TEXT,
    target_title TEXT,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Bảng document_files (quản lý file download)
CREATE TABLE IF NOT EXISTS document_files (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents_finals(doc_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT, -- pdf, docx, doc, other
    file_url TEXT NOT NULL,
    file_size BIGINT,
    local_path TEXT,
    download_status TEXT DEFAULT 'pending', -- pending, downloading, completed, failed
    downloaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_doc_relations_source ON document_relations(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_relations_target ON document_relations(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_session ON document_versions(session_id);
CREATE INDEX IF NOT EXISTS idx_crawl_sessions_status ON crawl_sessions(status);
CREATE INDEX IF NOT EXISTS idx_doc_urls_status ON doc_urls(status);
CREATE INDEX IF NOT EXISTS idx_doc_urls_doc_id ON doc_urls(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_files_doc_id ON document_files(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_files_status ON document_files(download_status);

-- ============================================================
-- VIEWS (Analytics & Reporting)
-- ============================================================

-- 1. Sessions overview
CREATE OR REPLACE VIEW v_sessions AS
SELECT 
    session_id,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at))/60 AS duration_minutes,
    status,
    total_docs,
    new_versions,
    unchanged_docs,
    ROUND(100.0 * new_versions / NULLIF(total_docs, 0), 2) AS change_rate_percent
FROM crawl_sessions
ORDER BY session_id DESC;

COMMENT ON VIEW v_sessions IS 'Tổng quan các phiên crawl: thời gian, số lượng docs, tỉ lệ thay đổi';

-- 2. Document history
CREATE OR REPLACE VIEW v_document_history AS
SELECT 
    dv.doc_id,
    df.title,
    dv.version_id,
    dv.crawled_at,
    dv.session_id,
    cs.started_at AS session_started,
    dv.source_snapshot_date,
    dv.diff_summary,
    ROW_NUMBER() OVER (PARTITION BY dv.doc_id ORDER BY dv.crawled_at DESC) AS version_number
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id
LEFT JOIN crawl_sessions cs ON dv.session_id = cs.session_id;

COMMENT ON VIEW v_document_history IS 'Lịch sử các phiên bản của văn bản với version number';

-- 3. Recent changes
CREATE OR REPLACE VIEW v_recent_changes AS
SELECT 
    dv.doc_id,
    df.title,
    df.url,
    dv.crawled_at,
    dv.session_id,
    dv.diff_summary->>'changed_fields' AS changed_fields,
    (dv.diff_summary->>'relations_added')::int AS relations_added,
    (dv.diff_summary->>'relations_removed')::int AS relations_removed,
    df.update_date AS source_update_date
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id
WHERE dv.diff_summary IS NOT NULL
ORDER BY dv.crawled_at DESC;

COMMENT ON VIEW v_recent_changes IS 'Các thay đổi gần đây: fields thay đổi, quan hệ thêm/xóa';

-- 4. Relations detailed
CREATE OR REPLACE VIEW v_relations_detailed AS
SELECT 
    dr.id,
    dr.source_doc_id,
    df_source.title AS source_title,
    dr.relation_type,
    dr.target_doc_id,
    dr.target_title,
    df_target.title AS target_title_from_db,
    dr.target_url,
    dr.resolved,
    CASE 
        WHEN df_target.doc_id IS NOT NULL THEN 'Có trong DB'
        ELSE 'Chưa crawl'
    END AS target_status
FROM document_relations dr
JOIN documents_finals df_source ON dr.source_doc_id = df_source.doc_id
LEFT JOIN documents_finals df_target ON dr.target_doc_id = df_target.doc_id;

COMMENT ON VIEW v_relations_detailed IS 'Chi tiết quan hệ văn bản với trạng thái target (có trong DB hay chưa)';

-- 5. Crawl queue status
CREATE OR REPLACE VIEW v_crawl_queue AS
SELECT 
    du.id,
    du.url,
    du.doc_id,
    du.title,
    du.status,
    du.priority,
    du.added_at,
    du.last_attempt_at,
    du.error_message,
    CASE 
        WHEN df.doc_id IS NOT NULL THEN 'Đã crawl'
        ELSE 'Chưa crawl'
    END AS crawl_status,
    df.last_crawled
FROM doc_urls du
LEFT JOIN documents_finals df ON du.doc_id = df.doc_id
ORDER BY du.priority DESC, du.added_at ASC;

COMMENT ON VIEW v_crawl_queue IS 'Danh sách URL chờ crawl với trạng thái và ưu tiên';

-- 6. Document files summary
CREATE OR REPLACE VIEW v_document_files_summary AS
SELECT 
    df.doc_id,
    df.title,
    df.url,
    COUNT(dfiles.id) AS total_files,
    COUNT(CASE WHEN dfiles.download_status = 'completed' THEN 1 END) AS downloaded_files,
    COUNT(CASE WHEN dfiles.download_status = 'pending' THEN 1 END) AS pending_files,
    COUNT(CASE WHEN dfiles.download_status = 'failed' THEN 1 END) AS failed_files,
    STRING_AGG(DISTINCT dfiles.file_type, ', ' ORDER BY dfiles.file_type) AS file_types,
    MAX(dfiles.downloaded_at) AS last_download_at
FROM documents_finals df
LEFT JOIN document_files dfiles ON df.doc_id = dfiles.doc_id
GROUP BY df.doc_id, df.title, df.url
ORDER BY df.last_crawled DESC;

COMMENT ON VIEW v_document_files_summary IS 'Tổng hợp files của văn bản: tổng số, đã tải, pending, failed';

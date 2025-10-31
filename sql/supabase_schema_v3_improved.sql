-- ============================================================
-- SUPABASE SCHEMA V3 - IMPROVED & NORMALIZED
-- Tách riêng metadata, chuẩn hóa relations, thêm audit logs
-- ============================================================

-- ============================================================
-- 1. CORE TABLES (Bảng chính)
-- ============================================================

-- 1.1. Documents (Văn bản - bảng trung tâm)
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    
    -- Dates
    issue_date DATE,           -- Ngày ban hành
    effective_date DATE,       -- Ngày hiệu lực
    expire_date DATE,          -- Ngày hết hiệu lực
    update_date DATE,          -- Ngày cập nhật (từ website)
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'active', -- active, expired, replaced
    
    -- Tracking
    content_hash TEXT NOT NULL,
    last_crawled_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.2. Document Metadata (Thông tin chi tiết văn bản)
CREATE TABLE IF NOT EXISTS document_metadata (
    doc_id TEXT PRIMARY KEY REFERENCES documents(doc_id) ON DELETE CASCADE,
    
    -- Thông tin cơ bản
    so_hieu TEXT,              -- Số hiệu
    loai_van_ban TEXT,         -- Loại văn bản
    linh_vuc TEXT,             -- Lĩnh vực
    co_quan_ban_hanh TEXT,     -- Cơ quan ban hành
    nguoi_ky TEXT,             -- Người ký
    
    -- Nội dung
    trich_yeu TEXT,            -- Trích yếu
    noi_dung_tom_tat TEXT,     -- Nội dung tóm tắt
    
    -- Metadata khác (JSONB cho flexibility)
    extra_fields JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.3. Document Relations (Quan hệ văn bản)
CREATE TABLE IF NOT EXISTS document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    target_doc_id TEXT REFERENCES documents(doc_id) ON DELETE SET NULL,
    
    -- Relation info
    relation_type TEXT NOT NULL, -- sua_doi, thay_the, huong_dan, thi_hanh, etc.
    target_url TEXT,
    target_title TEXT,
    
    -- Status
    is_resolved BOOLEAN DEFAULT false, -- target_doc_id đã được crawl chưa
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(source_doc_id, relation_type, target_url)
);

-- ============================================================
-- 2. FILES & DOWNLOADS
-- ============================================================

-- 2.1. Document Files (File đính kèm)
CREATE TABLE IF NOT EXISTS document_files (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    
    -- File info
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- pdf, doc, docx
    file_url TEXT NOT NULL,
    file_size BIGINT,
    
    -- Storage
    storage_bucket TEXT,       -- tvpl-files, download-pending
    storage_path TEXT,         -- path trong bucket
    
    -- Download status
    download_status TEXT DEFAULT 'pending', -- pending, downloading, completed, failed
    download_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    
    downloaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(doc_id, file_url)
);

-- ============================================================
-- 3. CRAWL MANAGEMENT
-- ============================================================

-- 3.1. Crawl Sessions (Phiên crawl)
CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    
    -- Session info
    session_type TEXT DEFAULT 'manual', -- manual, scheduled, api
    started_by TEXT,           -- user/system name
    
    -- Status
    status TEXT NOT NULL DEFAULT 'running', -- running, completed, failed, cancelled
    
    -- Stats
    total_docs INTEGER DEFAULT 0,
    new_docs INTEGER DEFAULT 0,
    updated_docs INTEGER DEFAULT 0,
    unchanged_docs INTEGER DEFAULT 0,
    failed_docs INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Notes
    notes TEXT
);

-- 3.2. Crawl Queue (Hàng đợi crawl)
CREATE TABLE IF NOT EXISTS crawl_queue (
    id BIGSERIAL PRIMARY KEY,
    
    -- URL info
    url TEXT NOT NULL UNIQUE,
    doc_id TEXT,
    title TEXT,
    
    -- Priority & Status
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    
    -- Retry logic
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Timing
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 3.3. Document Versions (Lịch sử thay đổi)
CREATE TABLE IF NOT EXISTS document_versions (
    version_id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES crawl_sessions(session_id),
    
    -- Version info
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    
    -- Changes
    changed_fields TEXT[],     -- Array of field names
    relations_added INTEGER DEFAULT 0,
    relations_removed INTEGER DEFAULT 0,
    
    -- Content snapshot (JSONB)
    content_snapshot JSONB,
    
    -- Timing
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    source_update_date DATE,
    
    UNIQUE(doc_id, version_number)
);

-- ============================================================
-- 4. AUDIT & LOGS
-- ============================================================

-- 4.1. Audit Logs (Nhật ký thay đổi)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Entity
    entity_type TEXT NOT NULL, -- document, file, relation
    entity_id TEXT NOT NULL,
    
    -- Action
    action TEXT NOT NULL,      -- create, update, delete
    changed_by TEXT,           -- user/system
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. INDEXES (Tối ưu query)
-- ============================================================

-- Documents
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_last_crawled ON documents(last_crawled_at DESC);
CREATE INDEX idx_documents_update_date ON documents(update_date DESC);

-- Metadata
CREATE INDEX idx_metadata_so_hieu ON document_metadata(so_hieu);
CREATE INDEX idx_metadata_loai_van_ban ON document_metadata(loai_van_ban);
CREATE INDEX idx_metadata_co_quan ON document_metadata(co_quan_ban_hanh);

-- Relations
CREATE INDEX idx_relations_source ON document_relations(source_doc_id);
CREATE INDEX idx_relations_target ON document_relations(target_doc_id);
CREATE INDEX idx_relations_type ON document_relations(relation_type);
CREATE INDEX idx_relations_resolved ON document_relations(is_resolved);

-- Files
CREATE INDEX idx_files_doc_id ON document_files(doc_id);
CREATE INDEX idx_files_status ON document_files(download_status);
CREATE INDEX idx_files_type ON document_files(file_type);

-- Crawl
CREATE INDEX idx_sessions_status ON crawl_sessions(status);
CREATE INDEX idx_sessions_started ON crawl_sessions(started_at DESC);
CREATE INDEX idx_queue_status ON crawl_queue(status);
CREATE INDEX idx_queue_priority ON crawl_queue(priority DESC, added_at ASC);

-- Versions
CREATE INDEX idx_versions_doc_id ON document_versions(doc_id);
CREATE INDEX idx_versions_session ON document_versions(session_id);
CREATE INDEX idx_versions_crawled ON document_versions(crawled_at DESC);

-- Audit
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- ============================================================
-- 6. VIEWS (Báo cáo & Analytics)
-- ============================================================

-- 6.1. Document Overview
CREATE OR REPLACE VIEW v_documents_overview AS
SELECT 
    d.doc_id,
    d.title,
    d.url,
    m.so_hieu,
    m.loai_van_ban,
    m.co_quan_ban_hanh,
    d.issue_date,
    d.effective_date,
    d.status,
    d.last_crawled_at,
    COUNT(DISTINCT dr.id) AS total_relations,
    COUNT(DISTINCT df.id) AS total_files,
    COUNT(DISTINCT CASE WHEN df.download_status = 'completed' THEN df.id END) AS downloaded_files
FROM documents d
LEFT JOIN document_metadata m ON d.doc_id = m.doc_id
LEFT JOIN document_relations dr ON d.doc_id = dr.source_doc_id
LEFT JOIN document_files df ON d.doc_id = df.doc_id
GROUP BY d.doc_id, d.title, d.url, m.so_hieu, m.loai_van_ban, m.co_quan_ban_hanh, 
         d.issue_date, d.effective_date, d.status, d.last_crawled_at;

-- 6.2. Pending Downloads
CREATE OR REPLACE VIEW v_pending_downloads AS
SELECT 
    df.id,
    df.doc_id,
    d.title AS doc_title,
    df.file_name,
    df.file_type,
    df.file_url,
    df.download_status,
    df.download_attempts,
    df.last_error,
    df.created_at
FROM document_files df
JOIN documents d ON df.doc_id = d.doc_id
WHERE df.download_status IN ('pending', 'failed')
ORDER BY df.download_attempts ASC, df.created_at ASC;

-- 6.3. Recent Changes
CREATE OR REPLACE VIEW v_recent_changes AS
SELECT 
    dv.doc_id,
    d.title,
    dv.version_number,
    dv.changed_fields,
    dv.relations_added,
    dv.relations_removed,
    dv.crawled_at,
    cs.session_id,
    cs.session_type
FROM document_versions dv
JOIN documents d ON dv.doc_id = d.doc_id
LEFT JOIN crawl_sessions cs ON dv.session_id = cs.session_id
WHERE dv.changed_fields IS NOT NULL OR dv.relations_added > 0 OR dv.relations_removed > 0
ORDER BY dv.crawled_at DESC;

-- 6.4. Crawl Stats
CREATE OR REPLACE VIEW v_crawl_stats AS
SELECT 
    session_id,
    session_type,
    status,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at))/60 AS duration_minutes,
    total_docs,
    new_docs,
    updated_docs,
    unchanged_docs,
    failed_docs,
    ROUND(100.0 * updated_docs / NULLIF(total_docs, 0), 2) AS change_rate_percent
FROM crawl_sessions
ORDER BY session_id DESC;

-- ============================================================
-- 7. FUNCTIONS (Helper functions)
-- ============================================================

-- 7.1. Update document updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER metadata_updated_at
    BEFORE UPDATE ON document_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 8. COMMENTS (Documentation)
-- ============================================================

COMMENT ON TABLE documents IS 'Bảng chính lưu thông tin văn bản';
COMMENT ON TABLE document_metadata IS 'Metadata chi tiết của văn bản (số hiệu, loại, cơ quan...)';
COMMENT ON TABLE document_relations IS 'Quan hệ giữa các văn bản (sửa đổi, thay thế, hướng dẫn...)';
COMMENT ON TABLE document_files IS 'File đính kèm của văn bản (PDF, DOC, DOCX)';
COMMENT ON TABLE crawl_sessions IS 'Phiên crawl với thống kê';
COMMENT ON TABLE crawl_queue IS 'Hàng đợi URL cần crawl';
COMMENT ON TABLE document_versions IS 'Lịch sử thay đổi của văn bản';
COMMENT ON TABLE audit_logs IS 'Nhật ký thay đổi dữ liệu';

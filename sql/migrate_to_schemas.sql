-- ============================================================
-- MIGRATION SCRIPT: public → tvpl/tnpl/system schemas
-- KHÔNG MẤT DỮ LIỆU - Chỉ di chuyển bảng sang schema mới
-- ============================================================

-- ============================================================
-- BƯỚC 1: TẠO SCHEMAS MỚI
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tvpl;
CREATE SCHEMA IF NOT EXISTS tnpl;
CREATE SCHEMA IF NOT EXISTS system;

-- ============================================================
-- BƯỚC 2: KIỂM TRA VÀ TẠO/DI CHUYỂN BẢNG
-- ============================================================

-- 2.1. TVPL: Di chuyển nếu có, tạo mới nếu chưa có

-- document_finals
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'documents_finals') THEN
        ALTER TABLE public.documents_finals SET SCHEMA tvpl;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tvpl' AND table_name = 'document_finals') THEN
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
    END IF;
END $$;

-- document_relations
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_relations') THEN
        ALTER TABLE public.document_relations SET SCHEMA tvpl;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tvpl' AND table_name = 'document_relations') THEN
        CREATE TABLE tvpl.document_relations (
            id BIGSERIAL PRIMARY KEY,
            source_doc_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            target_doc_id TEXT,
            target_url TEXT,
            target_title TEXT,
            resolved BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;
END $$;

-- document_files
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_files') THEN
        ALTER TABLE public.document_files SET SCHEMA tvpl;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tvpl' AND table_name = 'document_files') THEN
        CREATE TABLE tvpl.document_files (
            id BIGSERIAL PRIMARY KEY,
            doc_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_url TEXT NOT NULL,
            file_size BIGINT,
            local_path TEXT,
            download_status TEXT DEFAULT 'pending',
            downloaded_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;
END $$;

-- document_versions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_versions') THEN
        ALTER TABLE public.document_versions SET SCHEMA tvpl;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tvpl' AND table_name = 'document_versions') THEN
        CREATE TABLE tvpl.document_versions (
            version_id BIGSERIAL PRIMARY KEY,
            doc_id TEXT NOT NULL,
            version_hash TEXT NOT NULL,
            crawled_at TIMESTAMPTZ DEFAULT NOW(),
            content JSONB,
            diff_summary JSONB,
            source_snapshot_date DATE,
            session_id BIGINT
        );
    END IF;
END $$;

-- 2.2. TNPL: Di chuyển nếu có, tạo mới nếu chưa có

-- terms
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tnpl_terms') THEN
        ALTER TABLE public.tnpl_terms SET SCHEMA tnpl;
        ALTER TABLE tnpl.tnpl_terms RENAME TO terms;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tnpl' AND table_name = 'terms') THEN
        CREATE TABLE tnpl.terms (
            term_id SERIAL PRIMARY KEY,
            term_name VARCHAR(500) NOT NULL,
            definition TEXT,
            url VARCHAR(1000) UNIQUE NOT NULL,
            source_crawl VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;
END $$;

-- crawl_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tnpl_crawl_sessions') THEN
        ALTER TABLE public.tnpl_crawl_sessions SET SCHEMA tnpl;
        ALTER TABLE tnpl.tnpl_crawl_sessions RENAME TO crawl_sessions;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tnpl' AND table_name = 'crawl_sessions') THEN
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
    END IF;
END $$;

-- 2.3. SYSTEM: Di chuyển nếu có, tạo mới nếu chưa có

-- crawl_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'crawl_sessions') THEN
        ALTER TABLE public.crawl_sessions SET SCHEMA system;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'system' AND table_name = 'crawl_sessions') THEN
        CREATE TABLE system.crawl_sessions (
            session_id BIGSERIAL PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'RUNNING',
            started_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            total_docs INTEGER DEFAULT 0,
            new_versions INTEGER DEFAULT 0,
            unchanged_docs INTEGER DEFAULT 0
        );
    END IF;
END $$;

-- crawl_url
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'doc_urls') THEN
        ALTER TABLE public.doc_urls SET SCHEMA system;
        ALTER TABLE system.doc_urls RENAME TO crawl_url;
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'system' AND table_name = 'crawl_url') THEN
        CREATE TABLE system.crawl_url (
            id BIGSERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            doc_id TEXT,
            title TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            last_attempt_at TIMESTAMPTZ,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;
END $$;

-- audit_logs
CREATE TABLE IF NOT EXISTS system.audit_logs (
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
-- BƯỚC 3: TẠO LẠI INDEXES (sau khi di chuyển schema)
-- ============================================================

-- TVPL indexes
CREATE INDEX IF NOT EXISTS idx_tvpl_document_finals_hash ON tvpl.document_finals(hash);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_finals_last_crawled ON tvpl.document_finals(last_crawled DESC);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_relations_source ON tvpl.document_relations(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_relations_target ON tvpl.document_relations(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_files_doc_id ON tvpl.document_files(doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_files_status ON tvpl.document_files(download_status);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_versions_doc_id ON tvpl.document_versions(doc_id);

-- TNPL indexes
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_name ON tnpl.terms(term_name);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_created ON tnpl.terms(created_at DESC);

-- System indexes
CREATE INDEX IF NOT EXISTS idx_system_crawl_sessions_status ON system.crawl_sessions(status);
CREATE INDEX IF NOT EXISTS idx_system_crawl_url_status ON system.crawl_url(status);
CREATE INDEX IF NOT EXISTS idx_system_crawl_url_priority ON system.crawl_url(priority DESC);

-- ============================================================
-- BƯỚC 4: TẠO VIEWS (trong public schema)
-- ============================================================

-- 4.1. v_documents_overview
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

-- 4.2. v_pending_downloads
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

-- 4.3. v_tnpl_terms
CREATE OR REPLACE VIEW public.v_tnpl_terms AS
SELECT 
    term_id,
    term_name,
    LEFT(definition, 200) AS definition_preview,
    url,
    created_at
FROM tnpl.terms
ORDER BY created_at DESC;

-- 4.4. v_document_relations
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
-- BƯỚC 5: GRANT PERMISSIONS
-- ============================================================

GRANT USAGE ON SCHEMA tvpl TO anon, authenticated;
GRANT USAGE ON SCHEMA tnpl TO anon, authenticated;
GRANT USAGE ON SCHEMA system TO authenticated;

GRANT SELECT ON ALL TABLES IN SCHEMA tvpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA tnpl TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA system TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;

-- ============================================================
-- BƯỚC 6: VERIFY (Kiểm tra sau khi migrate)
-- ============================================================

-- Kiểm tra số lượng records
DO $$
BEGIN
    RAISE NOTICE 'TVPL documents: %', (SELECT COUNT(*) FROM tvpl.document_finals);
    RAISE NOTICE 'TVPL relations: %', (SELECT COUNT(*) FROM tvpl.document_relations);
    RAISE NOTICE 'TVPL files: %', (SELECT COUNT(*) FROM tvpl.document_files);
    RAISE NOTICE 'TNPL terms: %', (SELECT COUNT(*) FROM tnpl.terms);
    RAISE NOTICE 'System crawl_url: %', (SELECT COUNT(*) FROM system.crawl_url);
END $$;

-- ============================================================
-- HOÀN TẤT!
-- ============================================================

-- Sau khi chạy script này:
-- 1. Tất cả data đã được di chuyển sang schemas mới
-- 2. KHÔNG MẤT DỮ LIỆU
-- 3. Views đã được tạo trong public schema
-- 4. Code cũ vẫn hoạt động nếu query qua views

-- Cập nhật code để dùng schema mới:
-- - Thay: supabase.table('document_finals')
-- - Thành: supabase.table('tvpl.document_finals')
-- - Hoặc dùng views: supabase.table('v_documents_overview')

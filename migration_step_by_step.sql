-- ============================================================
-- BƯỚC 1: TẠO SCHEMAS
-- ============================================================

CREATE SCHEMA IF NOT EXISTS tvpl;
CREATE SCHEMA IF NOT EXISTS tnpl;
CREATE SCHEMA IF NOT EXISTS system;
CREATE SCHEMA IF NOT EXISTS views;

-- Kiểm tra schemas đã tạo
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name IN ('tvpl', 'tnpl', 'system');

-- ============================================================
-- BƯỚC 2: KIỂM TRA TABLES HIỆN TẠI
-- ============================================================

SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('public', 'tvpl', 'tnpl', 'system')
ORDER BY schemaname, tablename;

-- ============================================================
-- BƯỚC 3: DI CHUYỂN TABLES TỪ PUBLIC SANG SCHEMAS MỚI
-- ============================================================

-- 3.1. Di chuyển documents_finals -> tvpl.document_finals
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'documents_finals') THEN
        ALTER TABLE public.documents_finals SET SCHEMA tvpl;
        ALTER TABLE tvpl.documents_finals RENAME TO document_finals;
        RAISE NOTICE 'Đã di chuyển documents_finals -> tvpl.document_finals';
    END IF;
END $$;

-- 3.2. Di chuyển document_relations -> tvpl
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_relations') THEN
        ALTER TABLE public.document_relations SET SCHEMA tvpl;
        RAISE NOTICE 'Đã di chuyển document_relations -> tvpl';
    END IF;
END $$;

-- 3.3. Di chuyển document_files -> tvpl
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_files') THEN
        ALTER TABLE public.document_files SET SCHEMA tvpl;
        RAISE NOTICE 'Đã di chuyển document_files -> tvpl';
    END IF;
END $$;

-- 3.4. Di chuyển document_versions -> tvpl
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_versions') THEN
        ALTER TABLE public.document_versions SET SCHEMA tvpl;
        RAISE NOTICE 'Đã di chuyển document_versions -> tvpl';
    END IF;
END $$;

-- 3.5. Di chuyển doc_urls -> system.crawl_url
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'doc_urls') THEN
        ALTER TABLE public.doc_urls SET SCHEMA system;
        ALTER TABLE system.doc_urls RENAME TO crawl_url;
        RAISE NOTICE 'Đã di chuyển doc_urls -> system.crawl_url';
    END IF;
END $$;

-- 3.6. Di chuyển crawl_sessions -> system
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'crawl_sessions') THEN
        ALTER TABLE public.crawl_sessions SET SCHEMA system;
        RAISE NOTICE 'Đã di chuyển crawl_sessions -> system';
    END IF;
END $$;

-- 3.7. Di chuyển tnpl_terms -> tnpl.terms
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tnpl_terms') THEN
        ALTER TABLE public.tnpl_terms SET SCHEMA tnpl;
        ALTER TABLE tnpl.tnpl_terms RENAME TO terms;
        RAISE NOTICE 'Đã di chuyển tnpl_terms -> tnpl.terms';
    END IF;
END $$;

-- 3.8. Di chuyển tnpl_crawl_sessions -> tnpl.crawl_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tnpl_crawl_sessions') THEN
        ALTER TABLE public.tnpl_crawl_sessions SET SCHEMA tnpl;
        ALTER TABLE tnpl.tnpl_crawl_sessions RENAME TO crawl_sessions;
        RAISE NOTICE 'Đã di chuyển tnpl_crawl_sessions -> tnpl.crawl_sessions';
    END IF;
END $$;

-- ============================================================
-- BƯỚC 4: TẠO INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_tvpl_document_finals_hash ON tvpl.document_finals(hash);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_finals_last_crawled ON tvpl.document_finals(last_crawled DESC);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_relations_source ON tvpl.document_relations(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_relations_target ON tvpl.document_relations(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_files_doc_id ON tvpl.document_files(doc_id);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_files_status ON tvpl.document_files(download_status);
CREATE INDEX IF NOT EXISTS idx_tvpl_document_versions_doc_id ON tvpl.document_versions(doc_id);
CREATE INDEX IF NOT EXISTS idx_system_crawl_sessions_status ON system.crawl_sessions(status);
CREATE INDEX IF NOT EXISTS idx_system_crawl_url_status ON system.crawl_url(status);
CREATE INDEX IF NOT EXISTS idx_system_crawl_url_priority ON system.crawl_url(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_name ON tnpl.terms(term_name);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_created ON tnpl.terms(created_at DESC);

-- ============================================================
-- BƯỚC 5: TẠO VIEWS
-- ============================================================

CREATE OR REPLACE VIEW views.v_documents_overview AS
SELECT 
    d.doc_id,
    d.title,
    d.url,
    d.update_date,
    d.last_crawled,
    COUNT(DISTINCT r.relation_id) AS total_relations,
    COUNT(DISTINCT f.id) AS total_files
FROM tvpl.document_finals d
LEFT JOIN tvpl.document_relations r ON d.doc_id = r.source_doc_id
LEFT JOIN tvpl.document_files f ON d.doc_id = f.doc_id
GROUP BY d.doc_id, d.title, d.url, d.update_date, d.last_crawled;

CREATE OR REPLACE VIEW views.v_pending_downloads AS
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

CREATE OR REPLACE VIEW views.v_tnpl_terms AS
SELECT 
    term_id,
    term_name,
    LEFT(definition, 200) AS definition_preview,
    url,
    created_at
FROM tnpl.terms
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW views.v_document_relations AS
SELECT 
    r.relation_id,
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
-- BƯỚC 6: KIỂM TRA KẾT QUẢ
-- ============================================================

-- Kiểm tra số lượng records
SELECT 'tvpl.document_finals' as table_name, COUNT(*) as count FROM tvpl.document_finals
UNION ALL
SELECT 'tvpl.document_relations', COUNT(*) FROM tvpl.document_relations
UNION ALL
SELECT 'tvpl.document_files', COUNT(*) FROM tvpl.document_files
UNION ALL
SELECT 'tvpl.document_versions', COUNT(*) FROM tvpl.document_versions
UNION ALL
SELECT 'system.crawl_url', COUNT(*) FROM system.crawl_url
UNION ALL
SELECT 'system.crawl_sessions', COUNT(*) FROM system.crawl_sessions
UNION ALL
SELECT 'tnpl.terms', COUNT(*) FROM tnpl.terms
UNION ALL
SELECT 'tnpl.crawl_sessions', COUNT(*) FROM tnpl.crawl_sessions;

-- Kiểm tra tables trong mỗi schema
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('tvpl', 'tnpl', 'system')
ORDER BY schemaname, tablename;

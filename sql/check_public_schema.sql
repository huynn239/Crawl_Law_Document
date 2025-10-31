-- Kiểm tra tất cả tables và views trong public schema

-- 1. Liệt kê tất cả tables trong public
SELECT 
    'TABLE' as type,
    tablename as name,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 2. Liệt kê tất cả views trong public
SELECT 
    'VIEW' as type,
    viewname as name,
    definition
FROM pg_views 
WHERE schemaname = 'public'
ORDER BY viewname;

-- 3. Tổng hợp
SELECT 
    'TABLES' as category,
    COUNT(*) as count
FROM pg_tables 
WHERE schemaname = 'public'
UNION ALL
SELECT 
    'VIEWS',
    COUNT(*)
FROM pg_views 
WHERE schemaname = 'public';

-- 4. Kiểm tra tables/views cũ có thể xóa
-- (Tables cũ đã được di chuyển sang schemas khác)
SELECT 
    tablename as old_table,
    'Can be dropped - migrated to schemas' as note
FROM pg_tables 
WHERE schemaname = 'public'
  AND tablename NOT IN (
    'crawl_url', 'crawl_sessions', 'audit_logs',
    'document_finals', 'document_relations', 'document_files', 'document_versions',
    'tnpl_terms', 'tnpl_crawl_sessions',
    'v_documents_overview', 'v_pending_downloads', 'v_tnpl_terms', 'v_document_relations'
  );

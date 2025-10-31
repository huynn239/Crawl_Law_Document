-- Xóa toàn bộ dữ liệu để test lại crawl
-- Thứ tự xóa: child tables trước, parent tables sau

-- 1. Xóa document_relations (có foreign key tới documents_finals)
TRUNCATE TABLE document_relations CASCADE;

-- 2. Xóa document_versions (có foreign key tới documents_finals và crawl_sessions)
TRUNCATE TABLE document_versions CASCADE;

-- 3. Xóa crawl_sessions
TRUNCATE TABLE crawl_sessions CASCADE;

-- 4. Xóa documents_finals
TRUNCATE TABLE documents_finals CASCADE;

-- Reset sequences về 1
ALTER SEQUENCE documents_finals_id_seq RESTART WITH 1;
ALTER SEQUENCE document_versions_version_id_seq RESTART WITH 1;
ALTER SEQUENCE document_relations_id_seq RESTART WITH 1;
ALTER SEQUENCE crawl_sessions_session_id_seq RESTART WITH 1;

-- Kiểm tra kết quả
SELECT 'documents_finals' as table_name, COUNT(*) as count FROM documents_finals
UNION ALL
SELECT 'document_versions', COUNT(*) FROM document_versions
UNION ALL
SELECT 'document_relations', COUNT(*) FROM document_relations
UNION ALL
SELECT 'crawl_sessions', COUNT(*) FROM crawl_sessions;

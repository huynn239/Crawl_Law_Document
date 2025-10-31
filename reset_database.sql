-- Reset toàn bộ dữ liệu trong Supabase

-- Xóa dữ liệu
TRUNCATE TABLE 
  document_files,
  document_relations,
  document_versions,
  documents_finals,
  doc_urls,
  crawl_sessions
CASCADE;

-- Reset sequences
ALTER SEQUENCE crawl_sessions_session_id_seq RESTART WITH 1;
ALTER SEQUENCE document_versions_version_id_seq RESTART WITH 1;
ALTER SEQUENCE doc_urls_id_seq RESTART WITH 1;
ALTER SEQUENCE document_files_id_seq RESTART WITH 1;
ALTER SEQUENCE document_relations_id_seq RESTART WITH 1;

-- Xóa columns không dùng (nếu tồn tại)
ALTER TABLE documents_finals DROP COLUMN IF EXISTS effective_date;
ALTER TABLE documents_finals DROP COLUMN IF EXISTS expire_date;

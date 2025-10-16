-- Fix database schema issues
-- Run this after init_db.sql and migrate_schema.sql

-- 1. Add Foreign Key constraints
ALTER TABLE document_versions 
DROP CONSTRAINT IF EXISTS fk_versions_doc_id;

ALTER TABLE document_versions 
ADD CONSTRAINT fk_versions_doc_id 
FOREIGN KEY (doc_id) REFERENCES documents_finals(doc_id) 
ON DELETE CASCADE;

ALTER TABLE document_relations 
DROP CONSTRAINT IF EXISTS fk_relations_source_doc_id;

ALTER TABLE document_relations 
ADD CONSTRAINT fk_relations_source_doc_id 
FOREIGN KEY (source_doc_id) REFERENCES documents_finals(doc_id) 
ON DELETE CASCADE;

-- 2. Add missing indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_finals_hash ON documents_finals(hash);
CREATE INDEX IF NOT EXISTS idx_documents_finals_update_date ON documents_finals(update_date);
CREATE INDEX IF NOT EXISTS idx_document_versions_hash ON document_versions(version_hash);
CREATE INDEX IF NOT EXISTS idx_document_versions_doc_hash ON document_versions(doc_id, version_hash);
CREATE INDEX IF NOT EXISTS idx_document_relations_type ON document_relations(relation_type);

-- 3. Remove unused column (relations_summary không được code sử dụng)
ALTER TABLE documents_finals DROP COLUMN IF EXISTS relations_summary;

-- 4. Remove unused columns from init_db.sql
ALTER TABLE documents_finals DROP COLUMN IF EXISTS expire_date;


-- 5. Add comment for clarity
COMMENT ON TABLE documents_finals IS 'Bảng chính lưu trạng thái mới nhất của mỗi văn bản';
COMMENT ON TABLE document_versions IS 'Lịch sử thay đổi của văn bản (chỉ lưu khi có thay đổi)';
COMMENT ON TABLE document_relations IS 'Quan hệ giữa các văn bản (được rebuild mỗi lần có thay đổi)';
COMMENT ON TABLE crawl_sessions IS 'Theo dõi các phiên crawl';

-- 6. Clean duplicate versions before adding unique constraint
DELETE FROM document_versions a USING document_versions b
WHERE a.version_id > b.version_id 
AND a.doc_id = b.doc_id 
AND a.version_hash = b.version_hash;

-- Add constraint to prevent duplicate versions with same hash
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_doc_version 
ON document_versions(doc_id, version_hash);

-- ============================================
-- VIEW 1: Tổng quan văn bản (documents_overview)
-- ============================================
CREATE OR REPLACE VIEW documents_overview AS
SELECT 
    df.doc_id,
    df.title,
    df.url,
    df.update_date,
    df.last_crawled,
    (
        SELECT COUNT(*) 
        FROM document_relations dr 
        WHERE dr.source_doc_id = df.doc_id
    ) as total_relations,
    (
        SELECT COUNT(*) 
        FROM document_files dff 
        WHERE dff.doc_id = df.doc_id
    ) as total_files,
    df.metadata
FROM documents_finals df;


-- ============================================
-- VIEW 2: Quan hệ văn bản (relations_view)
-- ============================================
CREATE OR REPLACE VIEW relations_view AS
SELECT 
    dr.source_doc_id,
    df1.title as source_title,
    dr.relation_type,
    dr.target_doc_id,
    dr.target_title,
    dr.target_url,
    dr.resolved,
    CASE WHEN df2.doc_id IS NOT NULL THEN true ELSE false END as target_exists
FROM document_relations dr
LEFT JOIN documents_finals df1 ON dr.source_doc_id = df1.doc_id
LEFT JOIN documents_finals df2 ON dr.target_doc_id = df2.doc_id;


-- ============================================
-- VIEW 3: Lịch sử thay đổi (document_history)
-- ============================================
CREATE OR REPLACE VIEW document_history AS
SELECT 
    dv.version_id,
    dv.doc_id,
    df.title,
    dv.crawled_at,
    dv.session_id,
    dv.diff_summary,
    dv.source_snapshot_date
FROM document_versions dv
LEFT JOIN documents_finals df ON dv.doc_id = df.doc_id
ORDER BY dv.crawled_at DESC;


-- ============================================
-- VIEW 4: Thống kê sessions (sessions_summary)
-- ============================================
CREATE OR REPLACE VIEW sessions_summary AS
SELECT 
    session_id,
    status,
    started_at,
    completed_at,
    total_docs,
    new_versions,
    unchanged_docs,
    ROUND(EXTRACT(EPOCH FROM (completed_at - started_at))/60, 2) as duration_minutes
FROM crawl_sessions
ORDER BY started_at DESC;


-- ============================================
-- VIEW 5: Thống kê files (files_stats)
-- ============================================
CREATE OR REPLACE VIEW files_stats AS
SELECT 
    file_type,
    download_status,
    COUNT(*) as count
FROM document_files
GROUP BY file_type, download_status
ORDER BY file_type, download_status;


-- ============================================
-- VIEW 6: Thống kê tổng quan (stats_overview)
-- ============================================
CREATE OR REPLACE VIEW stats_overview AS
SELECT 
    (SELECT COUNT(*) FROM documents_finals) as total_documents,
    (SELECT COUNT(*) FROM document_relations) as total_relations,
    (SELECT COUNT(*) FROM document_versions) as total_versions,
    (SELECT COUNT(*) FROM document_files) as total_files,
    (SELECT COUNT(*) FROM crawl_sessions WHERE status = 'COMPLETED') as completed_sessions,
    (SELECT MAX(last_crawled) FROM documents_finals) as last_crawl_time;


-- ============================================
-- VIEW 7: Thống kê theo loại quan hệ (stats_by_relation_type)
-- ============================================
CREATE OR REPLACE VIEW stats_by_relation_type AS
SELECT 
    relation_type,
    COUNT(*) as total,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved,
    COUNT(CASE WHEN resolved = false THEN 1 END) as unresolved
FROM document_relations
GROUP BY relation_type
ORDER BY total DESC;

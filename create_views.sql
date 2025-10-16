-- Tạo các VIEW quan trọng cho database
-- Run: psql -U tvpl_user -d tvpl_crawl -f create_views.sql

-- 1. VIEW: Tổng quan sessions
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

COMMENT ON VIEW v_sessions IS 'Tổng quan các session crawl với tỷ lệ thay đổi';

-- 2. VIEW: Văn bản trong session (chi tiết)
CREATE OR REPLACE VIEW v_session_documents AS
SELECT 
    dv.session_id,
    dv.doc_id,
    df.title,
    df.url,
    df.metadata->>'loai_van_ban' AS loai_van_ban,
    dv.crawled_at,
    CASE 
        WHEN dv.diff_summary IS NOT NULL THEN 'Thay đổi'
        ELSE 'Lần đầu'
    END AS change_type,
    dv.diff_summary->>'changed_fields' AS changed_fields,
    (dv.diff_summary->>'relations_added')::int AS relations_added,
    (dv.diff_summary->>'relations_removed')::int AS relations_removed
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id;

COMMENT ON VIEW v_session_documents IS 'Chi tiết văn bản trong mỗi session';

-- 3. VIEW: Lịch sử version của văn bản
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

COMMENT ON VIEW v_document_history IS 'Lịch sử thay đổi của từng văn bản';

-- 4. VIEW: Thống kê quan hệ văn bản
CREATE OR REPLACE VIEW v_document_relations_summary AS
SELECT 
    df.doc_id,
    df.title,
    df.metadata->>'loai_van_ban' AS loai_van_ban,
    COUNT(dr.id) AS total_relations,
    COUNT(DISTINCT dr.relation_type) AS relation_types_count,
    STRING_AGG(DISTINCT dr.relation_type, ', ' ORDER BY dr.relation_type) AS relation_types,
    df.last_crawled
FROM documents_finals df
LEFT JOIN document_relations dr ON df.doc_id = dr.source_doc_id
GROUP BY df.doc_id, df.title, df.metadata, df.last_crawled;

COMMENT ON VIEW v_document_relations_summary IS 'Tổng hợp quan hệ của mỗi văn bản';

-- 5. VIEW: Văn bản thay đổi gần đây
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

COMMENT ON VIEW v_recent_changes IS 'Văn bản có thay đổi gần đây';

-- 6. VIEW: Top văn bản thay đổi nhiều
CREATE OR REPLACE VIEW v_most_changed_documents AS
SELECT 
    df.doc_id,
    df.title,
    df.url,
    df.metadata->>'loai_van_ban' AS loai_van_ban,
    COUNT(dv.version_id) AS version_count,
    MIN(dv.crawled_at) AS first_crawled,
    MAX(dv.crawled_at) AS last_crawled,
    MAX(df.update_date) AS last_update_date
FROM documents_finals df
JOIN document_versions dv ON df.doc_id = dv.doc_id
WHERE dv.diff_summary IS NOT NULL
GROUP BY df.doc_id, df.title, df.url, df.metadata
HAVING COUNT(dv.version_id) > 1
ORDER BY COUNT(dv.version_id) DESC;

COMMENT ON VIEW v_most_changed_documents IS 'Văn bản thay đổi nhiều nhất';

-- 7. VIEW: Thống kê theo loại văn bản
CREATE OR REPLACE VIEW v_stats_by_type AS
SELECT 
    metadata->>'loai_van_ban' AS loai_van_ban,
    COUNT(*) AS total_documents,
    COUNT(DISTINCT EXTRACT(YEAR FROM update_date)) AS years_span,
    MIN(update_date) AS oldest_update,
    MAX(update_date) AS newest_update,
    AVG((SELECT COUNT(*) FROM document_relations dr WHERE dr.source_doc_id = df.doc_id)) AS avg_relations
FROM documents_finals df
GROUP BY metadata->>'loai_van_ban'
ORDER BY COUNT(*) DESC;

COMMENT ON VIEW v_stats_by_type IS 'Thống kê theo loại văn bản';

-- 8. VIEW: Quan hệ văn bản với thông tin đầy đủ
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

COMMENT ON VIEW v_relations_detailed IS 'Quan hệ văn bản với thông tin chi tiết';

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tvpl_user;

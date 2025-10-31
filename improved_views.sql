-- Cải thiện views để xem thông tin văn bản logic hơn

-- View 1: Tổng quan văn bản (thông tin đầy đủ nhất)
CREATE OR REPLACE VIEW v_documents_overview AS
SELECT 
    df.doc_id,
    df.title,
    df.url,
    df.update_date,
    df.is_active,
    df.metadata->>'so_hieu' AS so_hieu,
    df.metadata->>'loai_van_ban' AS loai_van_ban,
    df.metadata->>'co_quan_ban_hanh' AS co_quan_ban_hanh,
    df.metadata->>'nguoi_ky' AS nguoi_ky,
    df.metadata->>'ngay_ban_hanh' AS ngay_ban_hanh,
    df.metadata->>'ngay_hieu_luc' AS ngay_hieu_luc,
    df.metadata->>'linh_vuc' AS linh_vuc,
    df.relations_summary,
    (SELECT COUNT(*) FROM document_relations WHERE source_doc_id = df.doc_id) AS total_relations,
    (SELECT COUNT(*) FROM document_files WHERE doc_id = df.doc_id) AS total_files,
    (SELECT COUNT(*) FROM document_versions WHERE doc_id = df.doc_id) AS total_versions,
    df.download_link,
    df.last_crawled,
    df.created_at,
    df.updated_at
FROM documents_finals df
ORDER BY df.last_crawled DESC;

COMMENT ON VIEW v_documents_overview IS 'Tổng quan văn bản với thông tin đầy đủ: metadata, số lượng quan hệ, files, versions';

-- View 2: Quan hệ văn bản (dễ đọc hơn)
CREATE OR REPLACE VIEW v_document_relations AS
SELECT 
    dr.source_doc_id,
    df_source.title AS source_title,
    dr.relation_type,
    COUNT(*) AS count
FROM document_relations dr
JOIN documents_finals df_source ON dr.source_doc_id = df_source.doc_id
GROUP BY dr.source_doc_id, df_source.title, dr.relation_type
ORDER BY dr.source_doc_id, dr.relation_type;

COMMENT ON VIEW v_document_relations IS 'Tổng hợp số lượng quan hệ văn bản theo loại (group by relation_type)';

-- View 3: Thống kê crawl sessions
CREATE OR REPLACE VIEW v_crawl_stats AS
SELECT 
    DATE(started_at) AS crawl_date,
    COUNT(*) AS total_sessions,
    SUM(total_docs) AS total_docs_crawled,
    SUM(new_versions) AS total_new_versions,
    SUM(unchanged_docs) AS total_unchanged,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60), 2) AS avg_duration_minutes,
    ROUND(100.0 * SUM(new_versions) / NULLIF(SUM(total_docs), 0), 2) AS avg_change_rate_percent
FROM crawl_sessions
WHERE status = 'COMPLETED'
GROUP BY DATE(started_at)
ORDER BY crawl_date DESC;

COMMENT ON VIEW v_crawl_stats IS 'Thống kê crawl theo ngày: tổng sessions, docs, change rate, thời gian trung bình';

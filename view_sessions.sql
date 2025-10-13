-- Xem tất cả sessions
SELECT 
    session_id,
    started_at,
    completed_at,
    total_docs,
    new_versions,
    unchanged_docs,
    status
FROM crawl_sessions
ORDER BY started_at DESC;

-- Xem chi tiết văn bản của session gần nhất
SELECT 
    dv.version_id,
    doc_id,
    d.url,
    d.title,
    d.metadata->>'so_hieu' as so_hieu,
    d.metadata->>'loai_van_ban' as loai_van_ban,
    dv.crawled_at
FROM document_versions dv
JOIN documents_finals d ON dv.doc_id = d.doc_id
WHERE dv.session_id = (SELECT session_id FROM crawl_sessions ORDER BY started_at DESC LIMIT 1)
ORDER BY dv.version_id;

-- Xem văn bản của session cụ thể (thay {session_id})
-- SELECT 
--     dv.version_id,
--     d.url,
--     d.title,
--     d.metadata->>'so_hieu' as so_hieu,
--     d.metadata->>'loai_van_ban' as loai_van_ban,
--     dv.crawled_at
-- FROM document_versions dv
-- JOIN documents_finals d ON dv.doc_id = d.doc_id
-- WHERE dv.session_id = {session_id}
-- ORDER BY dv.version_id;

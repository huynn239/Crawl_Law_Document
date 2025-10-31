-- Kiểm tra duplicate versions
SELECT 
    doc_id,
    version_hash,
    COUNT(*) as duplicate_count,
    STRING_AGG(version_id::text, ', ') as version_ids,
    MIN(crawled_at) as first_crawl,
    MAX(crawled_at) as last_crawl
FROM document_versions
GROUP BY doc_id, version_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Check relationships status

-- 1. Tổng số relationships
SELECT 
    COUNT(*) as total_relationships,
    COUNT(target_doc_id) as with_target_doc_id,
    COUNT(*) - COUNT(target_doc_id) as missing_target_doc_id
FROM relationships;

-- 2. Relationships theo type
SELECT 
    relationship_type,
    COUNT(*) as total,
    COUNT(target_doc_id) as with_target,
    COUNT(*) - COUNT(target_doc_id) as missing_target
FROM relationships
GROUP BY relationship_type
ORDER BY total DESC;

-- 3. Top 10 target URLs chưa có doc_id
SELECT 
    target_doc_url,
    COUNT(*) as count
FROM relationships
WHERE target_doc_id IS NULL
GROUP BY target_doc_url
ORDER BY count DESC
LIMIT 10;

-- 4. Check xem target URLs có trong doc_urls chưa
SELECT 
    r.target_doc_url,
    COUNT(*) as relationship_count,
    CASE 
        WHEN du.id IS NOT NULL THEN 'Exists in doc_urls'
        ELSE 'Not crawled yet'
    END as status
FROM relationships r
LEFT JOIN doc_urls du ON r.target_doc_url = du.url
WHERE r.target_doc_id IS NULL
GROUP BY r.target_doc_url, du.id
ORDER BY relationship_count DESC
LIMIT 20;

-- 5. Relationships có thể update (target đã crawl nhưng chưa link)
SELECT COUNT(*) as can_be_updated
FROM relationships r
JOIN doc_urls du ON r.target_doc_url = du.url
WHERE r.target_doc_id IS NULL
  AND du.status = 'crawled';

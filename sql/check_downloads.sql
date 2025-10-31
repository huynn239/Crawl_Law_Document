-- SQL Queries để check download status

-- 1. Tổng quan download status
SELECT 
    download_status,
    COUNT(*) as total,
    COUNT(DISTINCT doc_metadata_id) as unique_docs
FROM doc_files
GROUP BY download_status
ORDER BY download_status;

-- Expected output:
-- download_status | total | unique_docs
-- pending         | 150   | 50
-- downloaded      | 300   | 100
-- error           | 10    | 5

-- 2. Documents đã download đầy đủ files
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    COUNT(*) as total_files,
    COUNT(CASE WHEN df.download_status = 'downloaded' THEN 1 END) as downloaded_files
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
JOIN doc_files df ON dm.id = df.doc_metadata_id
GROUP BY du.doc_id, du.url, dm.so_hieu
HAVING COUNT(*) = COUNT(CASE WHEN df.download_status = 'downloaded' THEN 1 END)
ORDER BY du.doc_id DESC;

-- 3. Documents chưa download (có files pending)
SELECT * FROM v_pending_downloads
LIMIT 20;

-- 4. Check download status của 1 document cụ thể
SELECT * FROM v_download_status
WHERE doc_id = '677890';

-- 5. Documents có lỗi download
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    df.file_type,
    df.file_name,
    df.error_message
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
JOIN doc_files df ON dm.id = df.doc_metadata_id
WHERE df.download_status = 'error'
ORDER BY du.doc_id DESC;

-- 6. Thống kê download theo file type
SELECT 
    file_type,
    download_status,
    COUNT(*) as count
FROM doc_files
GROUP BY file_type, download_status
ORDER BY file_type, download_status;

-- Expected output:
-- file_type | download_status | count
-- pdf       | downloaded      | 100
-- pdf       | pending         | 50
-- doc       | downloaded      | 80
-- docx      | pending         | 20

-- 7. Documents cần download (priority list)
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    dm.ngay_ban_hanh,
    COUNT(*) as pending_files
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
JOIN doc_files df ON dm.id = df.doc_metadata_id
WHERE df.download_status = 'pending'
GROUP BY du.doc_id, du.url, dm.so_hieu, dm.ngay_ban_hanh
ORDER BY dm.ngay_ban_hanh DESC  -- Mới nhất trước
LIMIT 50;

-- 8. Update download status (sau khi download xong)
-- Example:
UPDATE doc_files
SET 
    download_status = 'downloaded',
    local_path = '/path/to/file.pdf',
    downloaded_at = NOW()
WHERE doc_metadata_id = (
    SELECT dm.id 
    FROM doc_metadata dm
    JOIN doc_urls du ON dm.doc_url_id = du.id
    WHERE du.doc_id = '677890'
)
AND file_type = 'pdf';

-- 9. Tìm documents có đủ metadata nhưng chưa có files
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    dm.ngay_ban_hanh
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
LEFT JOIN doc_files df ON dm.id = df.doc_metadata_id
WHERE df.id IS NULL  -- Không có files
ORDER BY dm.ngay_ban_hanh DESC;

-- 10. Storage usage (tổng dung lượng files đã download)
SELECT 
    file_type,
    COUNT(*) as total_files,
    SUM(file_size) as total_bytes,
    ROUND(SUM(file_size) / 1024.0 / 1024.0, 2) as total_mb,
    ROUND(SUM(file_size) / 1024.0 / 1024.0 / 1024.0, 2) as total_gb
FROM doc_files
WHERE download_status = 'downloaded'
  AND file_size IS NOT NULL
GROUP BY file_type
ORDER BY total_bytes DESC;

-- 11. Function để check xem doc đã download đủ files chưa
CREATE OR REPLACE FUNCTION is_fully_downloaded(p_doc_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_total INT;
    v_downloaded INT;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN df.download_status = 'downloaded' THEN 1 END)
    INTO v_total, v_downloaded
    FROM doc_urls du
    JOIN doc_metadata dm ON du.id = dm.doc_url_id
    JOIN doc_files df ON dm.id = df.doc_metadata_id
    WHERE du.doc_id = p_doc_id;
    
    IF v_total = 0 THEN
        RETURN FALSE;  -- Không có files
    END IF;
    
    RETURN v_total = v_downloaded;
END;
$$ LANGUAGE plpgsql;

-- Usage:
SELECT is_fully_downloaded('677890');
-- Returns: true/false

-- 12. Batch check download status
SELECT 
    doc_id,
    is_fully_downloaded(doc_id) as fully_downloaded
FROM doc_urls
WHERE status = 'crawled'
ORDER BY doc_id DESC
LIMIT 100;

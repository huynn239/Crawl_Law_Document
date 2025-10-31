-- Debug: Kiểm tra file_type trong document_files

-- 1. Xem tất cả file_type có trong bảng
SELECT DISTINCT file_type, COUNT(*) as count
FROM tvpl.document_files
GROUP BY file_type
ORDER BY count DESC;

-- 2. Xem files pending/failed theo file_type
SELECT 
    file_type,
    download_status,
    COUNT(*) as count
FROM tvpl.document_files
WHERE download_status IN ('pending', 'failed')
GROUP BY file_type, download_status
ORDER BY count DESC;

-- 3. Xem 10 files pending đầu tiên
SELECT id, doc_id, file_name, file_type, download_status
FROM tvpl.document_files
WHERE download_status IN ('pending', 'failed')
LIMIT 10;

-- 4. Kiểm tra view hiện tại
SELECT COUNT(*) as view_count FROM views.v_pending_downloads;

-- 5. Xem data trong view
SELECT * FROM views.v_pending_downloads LIMIT 10;

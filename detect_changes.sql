-- SQL queries để detect changes dựa trên ngay_cap_nhat

-- 1. Tìm văn bản có ngày cập nhật mới hơn trong DB
-- (Cần crawl lại để lấy phiên bản mới)
SELECT 
    du.url,
    dm.so_hieu,
    dm.ngay_cap_nhat as ngay_cap_nhat_cu,
    du.updated_at as lan_crawl_cuoi
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE du.status = 'crawled'
  AND dm.ngay_cap_nhat < CURRENT_DATE - INTERVAL '7 days'  -- Cũ hơn 7 ngày
ORDER BY dm.ngay_cap_nhat ASC
LIMIT 100;

-- 2. So sánh ngay_cap_nhat khi crawl mới
-- Logic trong n8n: Nếu ngay_cap_nhat mới != ngay_cap_nhat cũ → Tạo version mới
CREATE OR REPLACE FUNCTION check_document_changed(
    p_url TEXT,
    p_ngay_cap_nhat DATE,
    p_content_hash TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_latest_ngay_cap_nhat DATE;
    v_latest_hash TEXT;
BEGIN
    -- Lấy ngày cập nhật và hash mới nhất
    SELECT ngay_cap_nhat, content_hash
    INTO v_latest_ngay_cap_nhat, v_latest_hash
    FROM doc_metadata dm
    JOIN doc_urls du ON dm.doc_url_id = du.id
    WHERE du.url = p_url
    ORDER BY dm.version DESC
    LIMIT 1;
    
    -- Nếu chưa có data → Changed
    IF v_latest_ngay_cap_nhat IS NULL THEN
        RETURN TRUE;
    END IF;
    
    -- So sánh ngày cập nhật HOẶC hash
    IF p_ngay_cap_nhat > v_latest_ngay_cap_nhat OR p_content_hash != v_latest_hash THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 3. View để xem documents có thay đổi
CREATE OR REPLACE VIEW v_changed_documents AS
SELECT 
    du.url,
    dm.so_hieu,
    dm.ngay_cap_nhat,
    dm.version,
    dm.content_hash,
    dm.created_at as version_created_at,
    LAG(dm.ngay_cap_nhat) OVER (PARTITION BY du.url ORDER BY dm.version) as previous_ngay_cap_nhat,
    LAG(dm.content_hash) OVER (PARTITION BY du.url ORDER BY dm.version) as previous_hash
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE dm.version > 1  -- Chỉ lấy documents có nhiều hơn 1 version
ORDER BY dm.created_at DESC;

-- 4. Trigger để tự động tăng version khi insert duplicate
CREATE OR REPLACE FUNCTION auto_increment_version()
RETURNS TRIGGER AS $$
DECLARE
    v_max_version INT;
BEGIN
    -- Lấy version cao nhất hiện tại
    SELECT COALESCE(MAX(version), 0)
    INTO v_max_version
    FROM doc_metadata
    WHERE doc_url_id = NEW.doc_url_id;
    
    -- Set version mới
    NEW.version := v_max_version + 1;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_increment_version
BEFORE INSERT ON doc_metadata
FOR EACH ROW
EXECUTE FUNCTION auto_increment_version();

-- 5. Query để tìm documents cần re-crawl
-- (Dựa trên thời gian crawl cuối và ngày cập nhật)
SELECT 
    du.id,
    du.url,
    dm.so_hieu,
    dm.ngay_cap_nhat,
    du.updated_at as last_crawled,
    CURRENT_DATE - dm.ngay_cap_nhat as days_since_update
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE du.status = 'crawled'
  AND dm.version = (
      SELECT MAX(version) 
      FROM doc_metadata 
      WHERE doc_url_id = du.id
  )
  AND (
      -- Chưa crawl lại sau 30 ngày
      du.updated_at < NOW() - INTERVAL '30 days'
      OR
      -- Hoặc ngày cập nhật gần đây (trong 7 ngày) nhưng chưa crawl lại
      (dm.ngay_cap_nhat > CURRENT_DATE - INTERVAL '7 days' 
       AND du.updated_at < dm.ngay_cap_nhat)
  )
ORDER BY dm.ngay_cap_nhat DESC
LIMIT 100;

-- 6. Stats về document versions
SELECT 
    COUNT(DISTINCT du.url) as total_documents,
    COUNT(*) as total_versions,
    AVG(dm.version) as avg_versions_per_doc,
    MAX(dm.version) as max_versions,
    COUNT(CASE WHEN dm.version > 1 THEN 1 END) as docs_with_multiple_versions
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id;

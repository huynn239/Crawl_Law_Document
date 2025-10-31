-- Add last_update_date column to doc_urls table
ALTER TABLE doc_urls 
ADD COLUMN IF NOT EXISTS last_update_date DATE;

-- Add comment
COMMENT ON COLUMN doc_urls.last_update_date IS 'Ngày cập nhật văn bản (từ TVPL)';

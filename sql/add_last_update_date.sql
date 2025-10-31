-- Add last_update_date column to doc_urls table
ALTER TABLE doc_urls ADD COLUMN IF NOT EXISTS last_update_date DATE;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_doc_urls_last_update_date ON doc_urls(last_update_date);

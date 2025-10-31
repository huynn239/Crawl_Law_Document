-- Update view v_pending_downloads để chỉ hiển thị file_type = 'doc'

CREATE OR REPLACE VIEW views.v_pending_downloads AS
SELECT 
    f.id,
    f.doc_id,
    d.title AS doc_title,
    f.file_name,
    f.file_type,
    f.file_url,
    f.download_status,
    f.created_at
FROM tvpl.document_files f
JOIN tvpl.document_finals d ON f.doc_id = d.doc_id
WHERE f.download_status IN ('pending', 'failed')
  AND f.file_type = 'doc'
ORDER BY f.created_at ASC;

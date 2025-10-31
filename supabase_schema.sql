-- Schema cho Supabase - Thư viện pháp luật crawler
-- Tối ưu cho n8n workflow

-- 1. Bảng doc_urls - Danh sách URL cần crawl
CREATE TABLE doc_urls (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    doc_id TEXT,  -- Extract từ URL (677890.aspx → 677890)
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'crawling', 'crawled', 'error')),
    crawl_priority INT DEFAULT 0,
    last_crawl_attempt TIMESTAMPTZ,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doc_urls_status ON doc_urls(status);
CREATE INDEX idx_doc_urls_priority ON doc_urls(crawl_priority DESC);
CREATE INDEX idx_doc_urls_doc_id ON doc_urls(doc_id);

-- 2. Bảng doc_metadata - Thông tin chi tiết văn bản (Tối giản)
CREATE TABLE doc_metadata (
    id BIGSERIAL PRIMARY KEY,
    doc_url_id BIGINT REFERENCES doc_urls(id) ON DELETE CASCADE,
    doc_id TEXT,
    
    -- Chỉ giữ fields cần thiết cho query
    con_hieu_luc BOOLEAN,
    
    -- JSONB: Lưu toàn bộ doc_info
    extra_data JSONB,
    
    -- Tracking
    content_hash TEXT,
    version INT DEFAULT 1,
    
    -- Download status
    files_status TEXT DEFAULT 'not_downloaded' CHECK (files_status IN ('not_downloaded', 'partial', 'completed', 'error')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(doc_url_id, version)
);

CREATE INDEX idx_doc_metadata_doc_id ON doc_metadata(doc_id);
CREATE INDEX idx_doc_metadata_con_hieu_luc ON doc_metadata(con_hieu_luc);
CREATE INDEX idx_doc_metadata_hash ON doc_metadata(content_hash);
CREATE INDEX idx_doc_metadata_files_status ON doc_metadata(files_status);
CREATE INDEX idx_doc_metadata_extra_data ON doc_metadata USING GIN(extra_data);

-- 3. Bảng relationships - Quan hệ giữa các văn bản
CREATE TABLE relationships (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id BIGINT REFERENCES doc_metadata(id) ON DELETE CASCADE,
    target_doc_url TEXT NOT NULL,
    target_doc_id BIGINT REFERENCES doc_metadata(id) ON DELETE SET NULL,
    relationship_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_doc_id, target_doc_url, relationship_type)
);

CREATE INDEX idx_relationships_source ON relationships(source_doc_id);
CREATE INDEX idx_relationships_target_url ON relationships(target_doc_url);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- 4. Bảng doc_files - Files đã tải về (CHỈ LƯU FILE ĐÃ DOWNLOAD)
CREATE TABLE doc_files (
    id BIGSERIAL PRIMARY KEY,
    doc_metadata_id BIGINT UNIQUE REFERENCES doc_metadata(id) ON DELETE CASCADE,
    
    -- Thông tin file đã tải
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    local_path TEXT NOT NULL,  -- Path file đã tải (local hoặc S3)
    
    downloaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doc_files_type ON doc_files(file_type);

-- Function để extract doc_id từ URL
CREATE OR REPLACE FUNCTION extract_doc_id(url TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN (regexp_match(url, '-(\d+)\.aspx'))[1];
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Triggers để auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger để auto-extract doc_id khi insert
CREATE OR REPLACE FUNCTION auto_extract_doc_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.doc_id IS NULL THEN
        NEW.doc_id := extract_doc_id(NEW.url);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_extract_doc_id
BEFORE INSERT OR UPDATE ON doc_urls
FOR EACH ROW
EXECUTE FUNCTION auto_extract_doc_id();

CREATE TRIGGER update_doc_urls_updated_at BEFORE UPDATE ON doc_urls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_doc_metadata_updated_at BEFORE UPDATE ON doc_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger để auto-increment version khi insert duplicate
CREATE OR REPLACE FUNCTION auto_increment_version()
RETURNS TRIGGER AS $$
DECLARE
    v_max_version INT;
BEGIN
    -- Lấy version cao nhất hiện tại cho doc_url_id này
    SELECT COALESCE(MAX(version), 0)
    INTO v_max_version
    FROM doc_metadata
    WHERE doc_url_id = NEW.doc_url_id;
    
    -- Set version mới = max + 1
    NEW.version := v_max_version + 1;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_increment_version
BEFORE INSERT ON doc_metadata
FOR EACH ROW
EXECUTE FUNCTION auto_increment_version();

-- Trigger để auto-copy doc_id từ doc_urls
CREATE OR REPLACE FUNCTION auto_copy_doc_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.doc_id IS NULL THEN
        SELECT doc_id INTO NEW.doc_id
        FROM doc_urls
        WHERE id = NEW.doc_url_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_copy_doc_id
BEFORE INSERT ON doc_metadata
FOR EACH ROW
EXECUTE FUNCTION auto_copy_doc_id();

-- Trigger để auto-update files_status
CREATE OR REPLACE FUNCTION update_files_status()
RETURNS TRIGGER AS $$
DECLARE
    v_doc_metadata_id BIGINT;
    v_exists BOOLEAN;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_doc_metadata_id := OLD.doc_metadata_id;
    ELSE
        v_doc_metadata_id := NEW.doc_metadata_id;
    END IF;
    
    -- Check xem có file không
    SELECT EXISTS(
        SELECT 1 FROM doc_files WHERE doc_metadata_id = v_doc_metadata_id
    ) INTO v_exists;
    
    -- Update status
    UPDATE doc_metadata
    SET files_status = CASE 
        WHEN v_exists THEN 'completed'
        ELSE 'not_downloaded'
    END
    WHERE id = v_doc_metadata_id;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_files_status_insert
AFTER INSERT ON doc_files
FOR EACH ROW
EXECUTE FUNCTION update_files_status();

CREATE TRIGGER trigger_update_files_status_delete
AFTER DELETE ON doc_files
FOR EACH ROW
EXECUTE FUNCTION update_files_status();

-- Views hữu ích cho n8n
CREATE VIEW v_pending_crawls AS
SELECT 
    id,
    url,
    crawl_priority,
    retry_count,
    last_crawl_attempt
FROM doc_urls
WHERE status = 'pending'
ORDER BY crawl_priority DESC, created_at ASC
LIMIT 100;

CREATE VIEW v_document_summary AS
SELECT 
    du.url,
    du.doc_id,
    dm.so_hieu,
    dm.loai_van_ban,
    dm.noi_ban_hanh,
    dm.ngay_ban_hanh,
    dm.tinh_trang,
    dm.files_status,
    COUNT(DISTINCT r.id) as total_relationships,
    COUNT(DISTINCT df.id) as total_files
FROM doc_urls du
LEFT JOIN doc_metadata dm ON du.id = dm.doc_url_id
LEFT JOIN relationships r ON dm.id = r.source_doc_id
LEFT JOIN doc_files df ON dm.id = df.doc_metadata_id
WHERE du.status = 'crawled'
GROUP BY du.url, du.doc_id, dm.so_hieu, dm.loai_van_ban, dm.noi_ban_hanh, dm.ngay_ban_hanh, dm.tinh_trang, dm.files_status;

-- View để check download status
CREATE VIEW v_download_status AS
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    dm.files_status,
    df.file_name,
    df.file_type,
    df.local_path,
    df.downloaded_at
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
LEFT JOIN doc_files df ON dm.id = df.doc_metadata_id
ORDER BY du.doc_id DESC;

-- View để tìm docs chưa download
CREATE VIEW v_pending_downloads AS
SELECT 
    du.doc_id,
    du.url,
    dm.so_hieu,
    dm.files_status
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE dm.files_status IN ('not_downloaded', 'partial', 'error')
ORDER BY du.doc_id DESC;

-- RLS (Row Level Security) - Optional nếu cần
ALTER TABLE doc_urls ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_files ENABLE ROW LEVEL SECURITY;

-- Policy cho authenticated users
CREATE POLICY "Allow all for authenticated users" ON doc_urls FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON doc_metadata FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON relationships FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON doc_files FOR ALL TO authenticated USING (true);

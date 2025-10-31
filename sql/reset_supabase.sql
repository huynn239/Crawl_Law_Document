-- Reset và recreate tables với schema mới (tối giản)

-- Drop existing tables
DROP TABLE IF EXISTS doc_files CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;
DROP TABLE IF EXISTS doc_metadata CASCADE;
DROP TABLE IF EXISTS doc_urls CASCADE;

-- Drop functions and triggers
DROP FUNCTION IF EXISTS extract_doc_id CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
DROP FUNCTION IF EXISTS auto_extract_doc_id CASCADE;
DROP FUNCTION IF EXISTS auto_increment_version CASCADE;
DROP FUNCTION IF EXISTS auto_copy_doc_id CASCADE;
DROP FUNCTION IF EXISTS update_files_status CASCADE;

-- Drop views
DROP VIEW IF EXISTS v_pending_crawls CASCADE;
DROP VIEW IF EXISTS v_document_summary CASCADE;
DROP VIEW IF EXISTS v_download_status CASCADE;
DROP VIEW IF EXISTS v_pending_downloads CASCADE;

-- Recreate tables
CREATE TABLE doc_urls (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    doc_id TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'crawling', 'crawled', 'error')),
    crawl_priority INT DEFAULT 0,
    last_crawl_attempt TIMESTAMPTZ,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE doc_metadata (
    id BIGSERIAL PRIMARY KEY,
    doc_url_id BIGINT UNIQUE REFERENCES doc_urls(id) ON DELETE CASCADE,
    doc_id TEXT,
    con_hieu_luc BOOLEAN,
    extra_data JSONB,
    content_hash TEXT,
    version INT DEFAULT 1,
    files_status TEXT DEFAULT 'not_downloaded' CHECK (files_status IN ('not_downloaded', 'partial', 'completed', 'error')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(doc_url_id, version)
);

CREATE TABLE relationships (
    id BIGSERIAL PRIMARY KEY,
    source_doc_id BIGINT REFERENCES doc_metadata(id) ON DELETE CASCADE,
    target_doc_url TEXT NOT NULL,
    target_doc_id BIGINT REFERENCES doc_metadata(id) ON DELETE SET NULL,
    relationship_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_doc_id, target_doc_url, relationship_type)
);

CREATE TABLE doc_files (
    id BIGSERIAL PRIMARY KEY,
    doc_metadata_id BIGINT UNIQUE REFERENCES doc_metadata(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    local_path TEXT NOT NULL,
    downloaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_doc_urls_status ON doc_urls(status);
CREATE INDEX idx_doc_urls_priority ON doc_urls(crawl_priority DESC);
CREATE INDEX idx_doc_urls_doc_id ON doc_urls(doc_id);

CREATE INDEX idx_doc_metadata_doc_id ON doc_metadata(doc_id);
CREATE INDEX idx_doc_metadata_con_hieu_luc ON doc_metadata(con_hieu_luc);
CREATE INDEX idx_doc_metadata_hash ON doc_metadata(content_hash);
CREATE INDEX idx_doc_metadata_files_status ON doc_metadata(files_status);
CREATE INDEX idx_doc_metadata_extra_data ON doc_metadata USING GIN(extra_data);

CREATE INDEX idx_relationships_source ON relationships(source_doc_id);
CREATE INDEX idx_relationships_target_url ON relationships(target_doc_url);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

CREATE INDEX idx_doc_files_type ON doc_files(file_type);

-- Functions
CREATE OR REPLACE FUNCTION extract_doc_id(url TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN (regexp_match(url, '-(\d+)\.aspx'))[1];
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auto_extract_doc_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.doc_id IS NULL THEN
        NEW.doc_id := extract_doc_id(NEW.url);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auto_increment_version()
RETURNS TRIGGER AS $$
DECLARE
    v_max_version INT;
BEGIN
    SELECT COALESCE(MAX(version), 0)
    INTO v_max_version
    FROM doc_metadata
    WHERE doc_url_id = NEW.doc_url_id;
    
    NEW.version := v_max_version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auto_copy_doc_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.doc_id IS NULL THEN
        SELECT doc_id INTO NEW.doc_id FROM doc_urls WHERE id = NEW.doc_url_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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
    
    SELECT EXISTS(SELECT 1 FROM doc_files WHERE doc_metadata_id = v_doc_metadata_id) INTO v_exists;
    
    UPDATE doc_metadata
    SET files_status = CASE WHEN v_exists THEN 'completed' ELSE 'not_downloaded' END
    WHERE id = v_doc_metadata_id;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers
CREATE TRIGGER trigger_auto_extract_doc_id
BEFORE INSERT OR UPDATE ON doc_urls
FOR EACH ROW EXECUTE FUNCTION auto_extract_doc_id();

CREATE TRIGGER update_doc_urls_updated_at
BEFORE UPDATE ON doc_urls
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_auto_copy_doc_id
BEFORE INSERT ON doc_metadata
FOR EACH ROW EXECUTE FUNCTION auto_copy_doc_id();

CREATE TRIGGER trigger_auto_increment_version
BEFORE INSERT ON doc_metadata
FOR EACH ROW EXECUTE FUNCTION auto_increment_version();

CREATE TRIGGER update_doc_metadata_updated_at
BEFORE UPDATE ON doc_metadata
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_files_status_insert
AFTER INSERT ON doc_files
FOR EACH ROW EXECUTE FUNCTION update_files_status();

CREATE TRIGGER trigger_update_files_status_delete
AFTER DELETE ON doc_files
FOR EACH ROW EXECUTE FUNCTION update_files_status();

-- Views
CREATE VIEW v_pending_crawls AS
SELECT id, url, crawl_priority, retry_count, last_crawl_attempt
FROM doc_urls
WHERE status = 'pending'
ORDER BY crawl_priority DESC, created_at ASC
LIMIT 100;

CREATE VIEW v_document_summary AS
SELECT 
    du.url,
    du.doc_id,
    dm.extra_data->>'Số hiệu' as so_hieu,
    dm.extra_data->>'Loại văn bản' as loai_van_ban,
    dm.con_hieu_luc,
    dm.files_status,
    COUNT(r.id) as total_relationships
FROM doc_urls du
LEFT JOIN doc_metadata dm ON du.id = dm.doc_url_id
LEFT JOIN relationships r ON dm.id = r.source_doc_id
WHERE du.status = 'crawled'
GROUP BY du.url, du.doc_id, dm.extra_data, dm.con_hieu_luc, dm.files_status;

-- RLS
ALTER TABLE doc_urls ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for authenticated users" ON doc_urls FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON doc_metadata FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON relationships FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated users" ON doc_files FOR ALL TO authenticated USING (true);

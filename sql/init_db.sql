-- Tạo bảng documents_finals
CREATE TABLE IF NOT EXISTS documents_finals (
    doc_id text NOT NULL PRIMARY KEY,
    title text NOT NULL,
    url text NOT NULL,
    hash text NOT NULL,
    update_date date,
    effective_date date,
    expire_date date,
    is_active boolean DEFAULT true,
    metadata jsonb,
    relations_summary jsonb,
    last_crawled timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Tạo bảng document_versions
CREATE TABLE IF NOT EXISTS document_versions (
    version_id serial PRIMARY KEY,
    doc_id text NOT NULL,
    version_hash text NOT NULL,
    crawled_at timestamp without time zone DEFAULT now(),
    content jsonb,
    diff_summary jsonb,
    source_snapshot_date date
);

-- Tạo bảng document_relations
CREATE TABLE IF NOT EXISTS document_relations (
    id serial PRIMARY KEY,
    source_doc_id text NOT NULL,
    relation_type text NOT NULL,
    target_doc_id text,
    target_url text,
    target_title text,
    resolved boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);

-- Tạo bảng documents_snapshots
CREATE TABLE IF NOT EXISTS documents_snapshots (
    id serial PRIMARY KEY,
    doc_id text NOT NULL,
    title text NOT NULL,
    url text NOT NULL,
    update_date date,
    hash text NOT NULL,
    crawl_date date DEFAULT CURRENT_DATE,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now()
);

-- Tạo indexes
CREATE INDEX IF NOT EXISTS idx_doc_relations_source ON document_relations(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_relations_target ON document_relations(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_snapshots_doc_id ON documents_snapshots(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_snapshots_crawl_date ON documents_snapshots(crawl_date);

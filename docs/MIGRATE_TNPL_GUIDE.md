# 📦 Hướng dẫn Migrate TNPL từ PostgreSQL sang Supabase

## Bước 1: Chuẩn bị

### 1.1. Kiểm tra dữ liệu PostgreSQL local
```bash
# Kết nối PostgreSQL
psql -U postgres -d tvpl_crawler

# Kiểm tra số lượng records
SELECT COUNT(*) FROM tnpl_terms;
SELECT COUNT(*) FROM tnpl_crawl_sessions;
```

### 1.2. Thêm SUPABASE_SERVICE_ROLE_KEY vào .env
```bash
# .env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...  # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...  # ← THÊM DÒNG NÀY

# PostgreSQL local
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=tvpl_crawler
PG_USER=postgres
PG_PASSWORD=your_password
```

**Lấy service_role_key:**
1. Vào Supabase Dashboard
2. Settings → API
3. Copy "service_role" key (secret)

## Bước 2: Tạo bảng trên Supabase

### 2.1. Vào Supabase SQL Editor
```
Dashboard → SQL Editor → New Query
```

### 2.2. Chạy SQL sau:
```sql
-- Table: tnpl_terms
CREATE TABLE IF NOT EXISTS tnpl_terms (
    term_id SERIAL PRIMARY KEY,
    term_name VARCHAR(500) NOT NULL,
    definition TEXT,
    url VARCHAR(1000) UNIQUE NOT NULL,
    source_crawl VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table: tnpl_crawl_sessions
CREATE TABLE IF NOT EXISTS tnpl_crawl_sessions (
    session_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_terms INTEGER DEFAULT 0,
    new_terms INTEGER DEFAULT 0,
    updated_terms INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'RUNNING',
    notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_name ON tnpl_terms(term_name);
CREATE INDEX IF NOT EXISTS idx_tnpl_terms_created ON tnpl_terms(created_at DESC);
```

### 2.3. Enable RLS (Optional - nếu cần bảo mật)
```sql
-- Enable RLS
ALTER TABLE tnpl_terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE tnpl_crawl_sessions ENABLE ROW LEVEL SECURITY;

-- Policy cho phép service_role full access
CREATE POLICY "Service role full access" ON tnpl_terms
FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access" ON tnpl_crawl_sessions
FOR ALL TO service_role USING (true) WITH CHECK (true);
```

## Bước 3: Chạy Migration

```bash
python migrate_tnpl_to_supabase.py
```

Script sẽ:
1. ✅ Hiển thị SQL để tạo bảng (copy vào Supabase SQL Editor)
2. ✅ Đợi bạn nhấn Enter sau khi tạo bảng xong
3. ✅ Migrate dữ liệu từ PostgreSQL local → Supabase
4. ✅ Verify dữ liệu sau khi migrate

## Bước 4: Kiểm tra kết quả

### 4.1. Trên Supabase Dashboard
```
Table Editor → tnpl_terms
Table Editor → tnpl_crawl_sessions
```

### 4.2. Bằng SQL
```sql
-- Kiểm tra số lượng
SELECT COUNT(*) FROM tnpl_terms;
SELECT COUNT(*) FROM tnpl_crawl_sessions;

-- Xem sample data
SELECT * FROM tnpl_terms LIMIT 10;
```

## Xử lý lỗi

### Lỗi: "duplicate key value violates unique constraint"
→ Dữ liệu đã tồn tại, script sẽ tự động skip

### Lỗi: "permission denied"
→ Kiểm tra SUPABASE_SERVICE_ROLE_KEY trong .env

### Lỗi: "relation does not exist"
→ Chưa tạo bảng trên Supabase, quay lại Bước 2

## Backup (Khuyến nghị)

### Backup PostgreSQL local trước khi migrate
```bash
pg_dump -U postgres -d tvpl_crawler -t tnpl_terms -t tnpl_crawl_sessions > tnpl_backup.sql
```

### Restore nếu cần
```bash
psql -U postgres -d tvpl_crawler < tnpl_backup.sql
```

## Sau khi migrate xong

### Update code để dùng Supabase
```python
# Thay vì dùng PostgreSQL local
from tvpl_crawler.tnpl_db import TNPLDatabase
db = TNPLDatabase()  # PostgreSQL local

# Dùng Supabase
from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
result = supabase.table('tnpl_terms').select('*').execute()
```

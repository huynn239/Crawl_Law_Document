# Hướng dẫn fix database schema

## Cách 1: Dùng psql (khuyến nghị)

```powershell
# Tìm đường dẫn psql
where psql

# Hoặc dùng đường dẫn đầy đủ (thay đổi theo version PostgreSQL của bạn)
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U tvpl_user -d tvpl_crawl -f fix_db_schema.sql
```

## Cách 2: Dùng pgAdmin

1. Mở pgAdmin
2. Kết nối đến database `tvpl_crawl`
3. Mở Query Tool (Tools → Query Tool)
4. Copy nội dung file `fix_db_schema.sql` vào
5. Nhấn Execute (F5)

## Cách 3: Dùng Python (nếu đã cài psycopg2)

```powershell
# Cài psycopg2 nếu chưa có
pip install psycopg2-binary

# Chạy script
python run_fix_db.py
```

## Verify sau khi chạy

```sql
-- Kiểm tra Foreign Keys
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid IN ('document_versions'::regclass, 'document_relations'::regclass);

-- Kiểm tra Indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename IN ('documents_finals', 'document_versions', 'document_relations')
ORDER BY tablename, indexname;

-- Kiểm tra Unique Constraints
SELECT conname, conrelid::regclass 
FROM pg_constraint 
WHERE contype = 'u' 
AND conrelid = 'document_versions'::regclass;
```

## Kết quả mong đợi

- ✓ 2 Foreign Keys (document_versions → documents_finals, document_relations → documents_finals)
- ✓ 10+ Indexes (bao gồm hash, update_date, version_hash...)
- ✓ 1 Unique constraint (doc_id + version_hash)
- ✓ Xóa columns không dùng (relations_summary, expire_date, is_active)

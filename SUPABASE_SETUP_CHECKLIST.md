# ✅ Supabase Setup Checklist

## 📋 Bước 1: Tạo Project

1. Đăng nhập https://supabase.com
2. Tạo project mới
3. Chọn region gần nhất (Singapore)
4. Đợi project khởi tạo (~2 phút)

## 🗄️ Bước 2: Chạy Schema SQL

### Copy toàn bộ file `supabase_schema.sql`

1. Mở Supabase Dashboard
2. Vào **SQL Editor** (menu bên trái)
3. Click **New Query**
4. Copy toàn bộ nội dung file `supabase_schema.sql`
5. Paste vào editor
6. Click **Run** (hoặc Ctrl+Enter)

### Kết quả mong đợi:

```
✅ Success. No rows returned
```

## 🔍 Bước 3: Verify Tables

Vào **Table Editor**, kiểm tra 4 bảng đã được tạo:

### 1. doc_urls
- ✅ Columns: id, url, doc_id, status, crawl_priority, ...
- ✅ Indexes: idx_doc_urls_status, idx_doc_urls_priority, idx_doc_urls_doc_id
- ✅ Trigger: trigger_auto_extract_doc_id

### 2. doc_metadata
- ✅ Columns: id, doc_url_id, so_hieu, loai_van_ban, ngay_cap_nhat, content_hash, version, ...
- ✅ Indexes: idx_doc_metadata_so_hieu, idx_doc_metadata_ngay_cap_nhat, ...
- ✅ Trigger: trigger_auto_increment_version
- ✅ Foreign Key: doc_url_id → doc_urls(id)

### 3. relationships
- ✅ Columns: id, source_doc_id, target_doc_url, relationship_type, ...
- ✅ Indexes: idx_relationships_source, idx_relationships_target_url, ...
- ✅ Foreign Key: source_doc_id → doc_metadata(id)

### 4. doc_files
- ✅ Columns: id, doc_metadata_id, file_type, file_url, download_status, ...
- ✅ Indexes: idx_doc_files_doc, idx_doc_files_status
- ✅ Foreign Key: doc_metadata_id → doc_metadata(id)

## 🔧 Bước 4: Test Functions

Chạy các test queries sau trong SQL Editor:

### Test 1: Extract doc_id
```sql
SELECT extract_doc_id('https://thuvienphapluat.vn/van-ban/.../677890.aspx');
-- Expected: 677890
```

### Test 2: Insert URL với auto-extract doc_id
```sql
INSERT INTO doc_urls (url) 
VALUES ('https://thuvienphapluat.vn/van-ban/Test-677890.aspx');

SELECT url, doc_id FROM doc_urls WHERE url LIKE '%Test%';
-- Expected: doc_id = 677890 (tự động extract)
```

### Test 3: Auto-increment version
```sql
-- Insert version 1
INSERT INTO doc_urls (url) VALUES ('https://test.com/doc-123.aspx') RETURNING id;
-- Giả sử id = 1

INSERT INTO doc_metadata (doc_url_id, so_hieu) VALUES (1, 'Test-123');
SELECT version FROM doc_metadata WHERE doc_url_id = 1;
-- Expected: version = 1

-- Insert version 2
INSERT INTO doc_metadata (doc_url_id, so_hieu) VALUES (1, 'Test-123-v2');
SELECT version FROM doc_metadata WHERE doc_url_id = 1 ORDER BY version;
-- Expected: version = 1, 2
```

### Test 4: Views
```sql
SELECT * FROM v_pending_crawls;
-- Expected: Empty (chưa có data)

SELECT * FROM v_document_summary;
-- Expected: Empty (chưa có data)
```

## 🔐 Bước 5: Get API Credentials

1. Vào **Settings** → **API**
2. Copy các thông tin sau:

```
Project URL: https://xxxxx.supabase.co
API Key (anon, public): eyJhbGc...
Service Role Key: eyJhbGc... (KEEP SECRET!)
```

3. Lưu vào file `.env`:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

## 📊 Bước 6: Test Insert Data

### Test với sample data:

```sql
-- 1. Insert URL
INSERT INTO doc_urls (url, status) 
VALUES ('https://thuvienphapluat.vn/van-ban/Test-677890.aspx', 'pending')
RETURNING id;
-- Giả sử id = 1

-- 2. Insert metadata
INSERT INTO doc_metadata (
  doc_url_id, 
  so_hieu, 
  loai_van_ban,
  ngay_cap_nhat,
  content_hash
) VALUES (
  1,
  'Test-123/2025',
  'Thông tư',
  '2025-10-22',
  'abc123'
);

-- 3. Insert relationship
INSERT INTO relationships (
  source_doc_id,
  target_doc_url,
  target_text,
  relationship_type
) VALUES (
  1,
  'https://thuvienphapluat.vn/van-ban/Related-677891.aspx',
  'Văn bản liên quan',
  'van_ban_lien_quan'
);

-- 4. Insert file
INSERT INTO doc_files (
  doc_metadata_id,
  file_type,
  file_url,
  file_name
) VALUES (
  1,
  'pdf',
  'https://thuvienphapluat.vn/documents/download.aspx?id=xxx',
  'Test-123.pdf'
);

-- 5. Verify
SELECT 
  du.url,
  dm.so_hieu,
  dm.version,
  COUNT(r.id) as relationships,
  COUNT(df.id) as files
FROM doc_urls du
LEFT JOIN doc_metadata dm ON du.id = dm.doc_url_id
LEFT JOIN relationships r ON dm.id = r.source_doc_id
LEFT JOIN doc_files df ON dm.id = df.doc_metadata_id
GROUP BY du.url, dm.so_hieu, dm.version;
```

Expected output:
```
url                                    | so_hieu      | version | relationships | files
---------------------------------------|--------------|---------|---------------|------
https://...Test-677890.aspx           | Test-123/2025| 1       | 1             | 1
```

## 🧹 Bước 7: Cleanup Test Data

```sql
-- Xóa test data
DELETE FROM doc_urls WHERE url LIKE '%Test%';
```

## ✅ Checklist Summary

- [ ] Project created
- [ ] Schema SQL executed successfully
- [ ] 4 tables created
- [ ] All indexes created
- [ ] All triggers working
- [ ] Functions tested
- [ ] Views working
- [ ] API credentials saved
- [ ] Sample data inserted & verified
- [ ] Test data cleaned up

## 🚀 Next Steps

Sau khi setup xong:

1. **Test với Python**:
```bash
python supabase_transform.py data/result.json
```

2. **Setup N8N workflow**:
- Import workflow JSON
- Configure Supabase credentials
- Test với 1-2 documents

3. **Monitor**:
- Check Supabase Dashboard → Table Editor
- Verify data được insert đúng
- Check versions tự động tăng

## 📞 Troubleshooting

### Issue 1: Trigger không chạy
```sql
-- Check triggers
SELECT * FROM pg_trigger WHERE tgname LIKE '%doc_%';
```

### Issue 2: Foreign key error
```sql
-- Check constraints
SELECT * FROM information_schema.table_constraints 
WHERE table_name IN ('doc_urls', 'doc_metadata', 'relationships', 'doc_files');
```

### Issue 3: RLS blocking inserts
```sql
-- Disable RLS temporarily for testing
ALTER TABLE doc_urls DISABLE ROW LEVEL SECURITY;
ALTER TABLE doc_metadata DISABLE ROW LEVEL SECURITY;
ALTER TABLE relationships DISABLE ROW LEVEL SECURITY;
ALTER TABLE doc_files DISABLE ROW LEVEL SECURITY;
```

## 📚 Resources

- Supabase Docs: https://supabase.com/docs
- SQL Editor: https://supabase.com/dashboard/project/_/sql
- Table Editor: https://supabase.com/dashboard/project/_/editor

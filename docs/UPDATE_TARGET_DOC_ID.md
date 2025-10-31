# 🔄 Update Target Doc ID - Hướng dẫn

## 📋 Vấn Đề

Khi import relationships, `target_doc_id` chỉ được set nếu target document **đã tồn tại** trong database. Nếu target document chưa được crawl, `target_doc_id` sẽ là `NULL`.

### Ví dụ:

```
Document A → references → Document B (chưa crawl)
                          ↓
                    target_doc_id = NULL
```

Sau khi crawl Document B:

```
Document A → references → Document B (đã crawl)
                          ↓
                    target_doc_id = ??? (cần update)
```

## 🎯 Giải Pháp

### Option 1: Tự động update khi import

File `import_full_supabase.py` đã được update để tự động chạy update sau khi import:

```python
# 1. Import metadata
# 2. Import relationships
# 3. Import files
# 4. Update missing target_doc_id  ← MỚI!
```

**Chạy:**
```powershell
python import_full_supabase.py
```

**Output:**
```
[1/4] Importing metadata...
  Inserted: 50, Skipped: 0

[2/4] Importing relationships...
  Inserted: 150

[3/4] Importing files...
  Inserted: 50

[4/4] Updating missing target_doc_id...
  Updated: 25

Done!
```

### Option 2: Chạy update riêng

Nếu bạn muốn chỉ update mà không import lại:

```powershell
python update_target_doc_ids.py
```

**Output:**
```
🔍 Finding relationships with missing target_doc_id...
   Found: 100 relationships with NULL target_doc_id

🔄 Updating...
   ✓ Updated relationship 123
   ✓ Updated relationship 124
   ...

📊 SUMMARY:
   Total: 100
   Updated: 75
   Not found: 25

✅ Done!
```

## 📊 Check Status

### 1. Check tổng số relationships

```sql
SELECT 
    COUNT(*) as total_relationships,
    COUNT(target_doc_id) as with_target_doc_id,
    COUNT(*) - COUNT(target_doc_id) as missing_target_doc_id
FROM relationships;
```

**Kết quả:**
```
total_relationships | with_target_doc_id | missing_target_doc_id
--------------------|--------------------|-----------------------
        500         |        375         |          125
```

### 2. Check theo relationship type

```sql
SELECT 
    relationship_type,
    COUNT(*) as total,
    COUNT(target_doc_id) as with_target,
    COUNT(*) - COUNT(target_doc_id) as missing_target
FROM relationships
GROUP BY relationship_type
ORDER BY total DESC;
```

**Kết quả:**
```
relationship_type           | total | with_target | missing_target
----------------------------|-------|-------------|----------------
văn_bản_được_hướng_dẫn      |  200  |     150     |      50
văn_bản_hướng_dẫn           |  150  |     120     |      30
văn_bản_liên_quan           |  100  |      80     |      20
```

### 3. Check target URLs chưa crawl

```sql
SELECT 
    r.target_doc_url,
    COUNT(*) as relationship_count,
    CASE 
        WHEN du.id IS NOT NULL THEN 'Exists in doc_urls'
        ELSE 'Not crawled yet'
    END as status
FROM relationships r
LEFT JOIN doc_urls du ON r.target_doc_url = du.url
WHERE r.target_doc_id IS NULL
GROUP BY r.target_doc_url, du.id
ORDER BY relationship_count DESC
LIMIT 20;
```

### 4. Chạy file SQL

```powershell
# Copy nội dung từ check_relationships_status.sql
# Paste vào Supabase SQL Editor và Execute
```

## 🔄 Workflow Đầy Đủ

### Lần 1: Import batch đầu tiên

```powershell
# Crawl 50 documents
python -m tvpl_crawler links-basic -u "..." -o data/links1.json -m 5
python crawl_data_fast.py data/links1.json data/result1.json
python supabase_transform.py data/result1.json
python import_full_supabase.py
```

**Kết quả:**
- 50 documents imported
- 150 relationships created
- 75 có `target_doc_id` (target đã crawl)
- 75 có `target_doc_id = NULL` (target chưa crawl)

### Lần 2: Import batch thứ 2

```powershell
# Crawl 50 documents tiếp theo
python -m tvpl_crawler links-basic -u "..." -o data/links2.json --start-page 6 --end-page 10
python crawl_data_fast.py data/links2.json data/result2.json
python supabase_transform.py data/result2.json
python import_full_supabase.py
```

**Kết quả:**
- 50 documents mới imported
- 150 relationships mới created
- **Tự động update** 25 relationships cũ (từ batch 1) có target trong batch 2

### Lần 3: Update thủ công (nếu cần)

```powershell
# Nếu muốn force update tất cả
python update_target_doc_ids.py
```

## 🎯 Best Practices

### 1. Chạy update định kỳ

Sau mỗi lần import batch mới:

```powershell
python import_full_supabase.py  # Đã tự động update
```

Hoặc schedule trong N8N:

```
[Import Workflow]
    ↓
[Update Target Doc IDs]  ← Thêm node này
```

### 2. Monitor missing target_doc_id

```sql
-- Check hàng ngày
SELECT COUNT(*) - COUNT(target_doc_id) as missing
FROM relationships;
```

Nếu số lượng `missing` giảm dần → Good! Nghĩa là đang crawl đủ documents.

### 3. Prioritize crawling referenced documents

```sql
-- Lấy top URLs được reference nhiều nhất nhưng chưa crawl
SELECT 
    r.target_doc_url,
    COUNT(*) as reference_count
FROM relationships r
LEFT JOIN doc_urls du ON r.target_doc_url = du.url
WHERE du.id IS NULL  -- Chưa có trong doc_urls
GROUP BY r.target_doc_url
ORDER BY reference_count DESC
LIMIT 50;
```

Crawl những URLs này trước để tăng tỷ lệ `target_doc_id` được fill.

## 🐛 Troubleshooting

### Vấn đề: Update không tìm thấy target documents

**Nguyên nhân:** Target documents chưa được crawl

**Giải pháp:**
1. Check target URLs:
   ```sql
   SELECT target_doc_url FROM relationships WHERE target_doc_id IS NULL LIMIT 10;
   ```
2. Crawl những URLs đó
3. Chạy lại update

### Vấn đề: Update chậm

**Nguyên nhân:** Quá nhiều relationships cần update

**Giải pháp:**
1. Thêm index:
   ```sql
   CREATE INDEX idx_relationships_target_doc_id_null 
   ON relationships(target_doc_url) 
   WHERE target_doc_id IS NULL;
   ```
2. Batch update (đã có trong code)

### Vấn đề: Duplicate updates

**Nguyên nhân:** Chạy update nhiều lần

**Giải pháp:** Không sao! Code chỉ update relationships có `target_doc_id = NULL`, nên chạy nhiều lần cũng OK.

## 📈 Performance

- **Update 100 relationships**: ~5-10 giây
- **Update 1000 relationships**: ~30-60 giây
- **Update 10000 relationships**: ~5-10 phút

## 🎉 Kết Quả Mong Đợi

Sau khi crawl đủ documents và chạy update:

```sql
SELECT 
    COUNT(*) as total,
    COUNT(target_doc_id) as with_target,
    ROUND(COUNT(target_doc_id) * 100.0 / COUNT(*), 2) as percentage
FROM relationships;
```

**Mục tiêu:**
```
total | with_target | percentage
------|-------------|------------
 1000 |     950     |   95.00%
```

→ 95%+ relationships có `target_doc_id` là tốt!

## 📚 Tài Liệu Liên Quan

- [import_full_supabase.py](import_full_supabase.py) - Script import chính
- [update_target_doc_ids.py](update_target_doc_ids.py) - Script update riêng
- [check_relationships_status.sql](check_relationships_status.sql) - SQL queries
- [WORKFLOW_COMPLETE.md](WORKFLOW_COMPLETE.md) - Workflow đầy đủ

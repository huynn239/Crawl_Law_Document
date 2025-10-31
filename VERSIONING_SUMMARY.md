# 📚 Document Versioning System - Summary

## 🎯 Mục đích

Track thay đổi của văn bản pháp luật theo thời gian dựa trên `ngay_cap_nhat` từ website.

## 🔑 Key Concepts

### 1. Ngày cập nhật (ngay_cap_nhat)

- **Nguồn**: Từ file `links_*.json` khi crawl hyperlinks
- **Ý nghĩa**: Ngày website cập nhật văn bản lần cuối
- **Sử dụng**: Detect khi nào cần tạo version mới

### 2. Content Hash

- **Tính toán**: MD5 hash của `doc_info`
- **Ý nghĩa**: Fingerprint của nội dung văn bản
- **Sử dụng**: Detect thay đổi nội dung (backup cho ngay_cap_nhat)

### 3. Version

- **Auto-increment**: Tự động tăng khi insert duplicate
- **Start**: Version 1 cho lần đầu
- **Increment**: Version 2, 3, 4... cho các lần cập nhật

## 📊 Database Schema

```sql
doc_metadata (
  id BIGSERIAL PRIMARY KEY,
  doc_url_id BIGINT,
  
  -- Metadata
  so_hieu TEXT,
  loai_van_ban TEXT,
  ...
  
  -- Versioning (QUAN TRỌNG)
  ngay_cap_nhat DATE,      -- Từ website
  content_hash TEXT,        -- MD5 hash
  version INT DEFAULT 1,    -- Auto-increment
  
  created_at TIMESTAMPTZ,   -- Khi version này được tạo
  updated_at TIMESTAMPTZ,
  
  UNIQUE(doc_url_id, version)
)
```

## 🔄 Workflow Logic

### Khi crawl document mới:

```
1. Lấy ngay_cap_nhat từ links.json
2. Crawl document data
3. Tính content_hash
4. Query latest version từ DB
5. So sánh:
   - Nếu ngay_cap_nhat mới > cũ → Tạo version mới
   - Nếu content_hash khác → Tạo version mới
   - Nếu giống hệt → Skip hoặc update timestamp
```

### Example Timeline:

```
2025-10-15: Văn bản được ban hành
  → Version 1: ngay_cap_nhat = 2025-10-15

2025-10-20: Website cập nhật sửa lỗi
  → Version 2: ngay_cap_nhat = 2025-10-20

2025-11-01: Website cập nhật bổ sung
  → Version 3: ngay_cap_nhat = 2025-11-01
```

## 📁 Files Structure

```
data/
├── links_2025-10-22.json          # Có ngay_cap_nhat
├── result_2025-10-22.json         # Có ngay_cap_nhat từ links
└── result_2025-10-22_cleaned.json # Optimized version
```

### links.json format:
```json
[
  {
    "Stt": 1,
    "Url": "https://...",
    "Ten van ban": "...",
    "Ngay cap nhat": "22/10/2025"  ← QUAN TRỌNG
  }
]
```

### result.json format:
```json
[
  {
    "url": "https://...",
    "ngay_cap_nhat": "22/10/2025",  ← Từ links.json
    "doc_info": { ... },
    "tab4": { ... },
    "tab8": { ... }
  }
]
```

## 🚀 N8N Workflow

### Node 1: Crawl Hyperlinks
```bash
python n8n_node1_get_urls.py "..." 5
# Output: links với ngay_cap_nhat
```

### Node 2: Crawl Documents
```bash
python n8n_node2_crawl_docs.py urls.json 2
# Input: URLs từ Node 1 (có ngay_cap_nhat)
# Output: Documents với ngay_cap_nhat preserved
```

### Node 3: Check & Insert Versions
```javascript
// Pseudo-code
for each document:
  latest = query_latest_version(url)
  
  if not latest:
    insert(version=1)
  else if doc.ngay_cap_nhat > latest.ngay_cap_nhat:
    insert(version=latest.version+1)
  else if doc.content_hash != latest.content_hash:
    insert(version=latest.version+1)
  else:
    update_timestamp_only()
```

## 📈 Monitoring

### Query 1: Documents với nhiều versions
```sql
SELECT url, COUNT(*) as versions
FROM doc_metadata
GROUP BY url
HAVING COUNT(*) > 1
ORDER BY versions DESC;
```

### Query 2: Recent updates
```sql
SELECT url, version, ngay_cap_nhat, created_at
FROM doc_metadata
WHERE created_at > NOW() - INTERVAL '7 days'
  AND version > 1
ORDER BY created_at DESC;
```

### Query 3: Cần re-crawl
```sql
SELECT url, ngay_cap_nhat, updated_at
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE updated_at < NOW() - INTERVAL '30 days'
ORDER BY updated_at ASC
LIMIT 100;
```

## ⚠️ Important Notes

1. **Preserve ngay_cap_nhat**: Luôn giữ field này từ links.json → result.json → DB
2. **Auto-increment version**: Trigger trong DB tự động handle
3. **Unique constraint**: `(doc_url_id, version)` đảm bảo không duplicate
4. **Re-crawl strategy**: Mỗi 30 ngày hoặc khi detect ngay_cap_nhat mới

## 🔧 Maintenance

### Weekly:
- Check documents với nhiều versions
- Review recent changes
- Monitor storage growth

### Monthly:
- Re-crawl documents cũ (>30 days)
- Cleanup old versions (optional)
- Analyze change patterns

## 📊 Expected Metrics

- **Average versions per document**: 1.2 - 1.5
- **Documents with >3 versions**: <5%
- **New versions per day**: 10-50
- **Storage growth**: ~2-3% per month

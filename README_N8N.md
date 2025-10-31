# 🤖 N8N Workflow - Thư viện Pháp luật Crawler

## 📋 Tổng quan

Workflow tự động crawl văn bản pháp luật từ thuvienphapluat.vn và lưu vào Supabase với versioning.

## 🚀 Quick Start

```bash
# 1. Setup Supabase (chạy supabase_schema.sql)
# 2. Tạo .env file với SUPABASE_URL và SUPABASE_KEY
# 3. Test workflow:

# Crawl links (page 1-2)
python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links.json -m 2

# Crawl documents
python crawl_data_fast.py data/links.json data/result.json

# Transform
python supabase_transform.py data/result.json

# Import
python test_supabase_import.py
```

## 📖 Commands

### Crawl Hyperlinks

```bash
# Cách 1: Dùng max-pages (từ page 1)
python -m tvpl_crawler links-basic \
  -u "URL_WITH_{page}_PLACEHOLDER" \
  -o data/links.json \
  -m 5

# Cách 2: Dùng start-page và end-page
python -m tvpl_crawler links-basic \
  -u "URL_WITH_{page}_PLACEHOLDER" \
  -o data/links.json \
  --start-page 10 \
  --end-page 20
```

### Crawl Documents

```bash
python crawl_data_fast.py data/links.json data/result.json
```

### Transform to Supabase Format

```bash
python supabase_transform.py data/result.json
# Output: data/result_supabase.json
```

### Import to Supabase

```bash
python test_supabase_import.py
```

## 🔄 Workflow Logic

```
┌─────────────────────────────────────────┐
│ 1. Crawl Hyperlinks                     │
│    → links.json (có ngay_cap_nhat)      │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ 2. Crawl Documents                      │
│    → result.json (full data)            │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ 3. Transform                            │
│    → result_supabase.json               │
│    (doc_metadata, relationships, files) │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ 4. Import to Supabase                   │
│    - Check version by content_hash      │
│    - Insert if changed                  │
│    - Skip if same                       │
└─────────────────────────────────────────┘
```

## 🗄️ Database Schema

### Tables

1. **doc_urls** - Danh sách URLs cần crawl
2. **doc_metadata** - Metadata + raw_data (JSONB)
3. **relationships** - Quan hệ giữa văn bản + raw_data (JSONB)
4. **doc_files** - Files đã download

### Versioning

- Tự động tạo version mới khi `content_hash` thay đổi
- Trigger auto-increment version
- Unique constraint: `(doc_url_id, version)`

## 📊 Monitoring

```sql
-- Tổng số documents
SELECT COUNT(*) FROM doc_urls;

-- Documents mới nhất
SELECT * FROM v_document_summary ORDER BY created_at DESC LIMIT 10;

-- Documents có nhiều versions
SELECT url, COUNT(*) as versions
FROM doc_metadata dm
JOIN doc_urls du ON dm.doc_url_id = du.id
GROUP BY url
HAVING COUNT(*) > 1;

-- Pending downloads
SELECT * FROM v_pending_downloads LIMIT 10;
```

## 🔧 Configuration

### .env file

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
```

### URL Template Examples

```bash
# Tất cả văn bản 2025
"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}"

# Nghị định
"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=3&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}"

# Thông tư
"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=9&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}"
```

## 📁 File Structure

```
thuvienphapluat-crawler/
├── supabase_schema.sql          # Database schema
├── supabase_transform.py        # Transform script
├── test_supabase_import.py      # Import script
├── n8n_import_supabase.js       # N8N code node
├── .env                         # Config
├── data/
│   ├── links.json              # Crawled links
│   ├── result.json             # Crawled documents
│   └── result_supabase.json    # Transformed data
└── docs/
    ├── QUICKSTART.md
    ├── SETUP_N8N.md
    └── VERSIONING_SUMMARY.md
```

## 🎯 Best Practices

1. **Incremental Crawl**: Crawl từng batch nhỏ (5-10 pages)
2. **Check Changes**: Chỉ insert khi content_hash thay đổi
3. **Monitor**: Check logs và database thường xuyên
4. **Backup**: Backup database định kỳ
5. **Rate Limit**: Không crawl quá nhanh (respect website)

## 🐛 Troubleshooting

### Lỗi: "Table does not exist"
→ Chạy lại `supabase_schema.sql`

### Lỗi: "Duplicate key violation"
→ Bình thường, trigger sẽ tự tạo version mới

### Lỗi: "Connection timeout"
→ Check SUPABASE_URL và SUPABASE_KEY

### Documents không có version mới
→ Check `content_hash`, nếu giống nhau thì skip

## 📚 Documentation

- [QUICKSTART.md](QUICKSTART.md) - Setup nhanh trong 10 phút
- [SETUP_N8N.md](SETUP_N8N.md) - Setup N8N chi tiết
- [VERSIONING_SUMMARY.md](VERSIONING_SUMMARY.md) - Hiểu về versioning

## 🤝 Support

- Issues: GitHub Issues
- Docs: Xem các file .md trong repo

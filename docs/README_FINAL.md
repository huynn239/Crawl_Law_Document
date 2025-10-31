# 🚀 TVPL Crawler - Production Ready

## ✅ Setup Hoàn Tất

### 📁 Files Quan Trọng

```
thuvienphapluat-crawler/
├── reset_supabase.sql              # Reset database schema
├── supabase_transform.py           # Transform data
├── import_full_supabase.py         # Import to Supabase
├── n8n_workflow_final.json         # N8N workflow (simple)
├── N8N_WORKFLOW_DESIGN.md          # N8N workflow (detailed)
├── .env                            # Config (cần điền)
└── data/
    ├── links.json
    ├── result.json
    └── result_supabase.json
```

## 🎯 Quick Start (3 bước)

### Bước 1: Setup Supabase
```sql
-- 1. Tạo project tại https://supabase.com
-- 2. Vào SQL Editor
-- 3. Copy & Execute: reset_supabase.sql
```

### Bước 2: Config Local
```bash
# Edit .env file
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...

# Install dependencies
pip install supabase python-dotenv
```

### Bước 3: Test Workflow
```bash
# Test full workflow
python -m tvpl_crawler links-basic -u "URL" -o data/links.json --start-page 1 --end-page 2
python crawl_data_fast.py data/links.json data/result.json
python supabase_transform.py data/result.json
python import_full_supabase.py
```

## 🤖 Setup N8N

### Option 1: Simple (Khuyến nghị)
```bash
# 1. Install N8N
npx n8n

# 2. Import workflow
# - Mở http://localhost:5678
# - Import file: n8n_workflow_final.json
# - Test workflow
```

### Option 2: Advanced
- Đọc file: `N8N_WORKFLOW_DESIGN.md`
- Tạo workflow theo hướng dẫn chi tiết
- Customize theo nhu cầu

## 📊 Database Schema (Tối Giản)

### doc_metadata
```sql
- doc_id TEXT              -- ID văn bản
- con_hieu_luc BOOLEAN     -- Còn hiệu lực?
- extra_data JSONB         -- Toàn bộ thông tin
- content_hash TEXT        -- Detect thay đổi
```

### Query Examples
```sql
-- Tìm văn bản còn hiệu lực
SELECT doc_id, extra_data->>'Số hiệu' as so_hieu
FROM doc_metadata
WHERE con_hieu_luc = true;

-- Tìm theo loại văn bản
SELECT * FROM doc_metadata
WHERE extra_data->>'Loại văn bản' = 'Nghị định';

-- Tìm relationships
SELECT 
    s.doc_id as source,
    t.doc_id as target,
    r.relationship_type
FROM relationships r
JOIN doc_metadata s ON r.source_doc_id = s.id
LEFT JOIN doc_metadata t ON r.target_doc_id = t.id
WHERE s.doc_id = '677999';
```

## 🔄 Workflow Commands

### Crawl Hyperlinks
```bash
# Crawl page 1-10
python -m tvpl_crawler links-basic \
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" \
  -o data/links.json \
  --start-page 1 \
  --end-page 10
```

### Crawl Documents
```bash
python crawl_data_fast.py data/links.json data/result.json
```

### Transform
```bash
python supabase_transform.py data/result.json
```

### Import
```bash
python import_full_supabase.py
```

## 📈 Monitoring

### Check Data
```sql
SELECT COUNT(*) FROM doc_urls;
SELECT COUNT(*) FROM doc_metadata;
SELECT COUNT(*) FROM relationships;
SELECT COUNT(*) FROM doc_files;
```

### Check Recent
```sql
SELECT * FROM v_document_summary
ORDER BY created_at DESC
LIMIT 10;
```

## 🎯 Production Tips

### 1. Incremental Crawl
- Crawl 5-10 pages/day
- Tránh overload
- Dễ monitor

### 2. Error Handling
- Check logs trong N8N
- Monitor error rate
- Setup alerts

### 3. Backup
- Export Supabase data định kỳ
- Backup files trong data/
- Version control code

### 4. Optimization
- Batch size: 10-50 items
- Parallel processing khi có thể
- Cache doc_urls lookup

## 🐛 Troubleshooting

### Lỗi: "Table does not exist"
→ Chạy lại `reset_supabase.sql`

### Lỗi: "Duplicate key"
→ Bình thường, UNIQUE constraint sẽ skip

### Lỗi: "Connection timeout"
→ Check SUPABASE_URL và SUPABASE_KEY

### Relationships không insert
→ Source document phải tồn tại trước

## 📚 Documentation

- `N8N_WORKFLOW_DESIGN.md` - N8N workflow chi tiết
- `QUICKSTART.md` - Hướng dẫn nhanh
- `VERSIONING_SUMMARY.md` - Versioning system

## 🎉 Next Steps

1. ✅ Test với data nhỏ (2-5 pages)
2. ✅ Verify data trong Supabase
3. ✅ Setup N8N workflow
4. ✅ Test N8N workflow
5. ✅ Enable schedule (daily 2AM)
6. ⏳ Monitor trong 1 tuần
7. ⏳ Scale up (10-20 pages/day)
8. ⏳ Setup backup strategy

## 💡 Tips

- Bắt đầu nhỏ (2-5 pages)
- Monitor logs thường xuyên
- Backup data định kỳ
- Document mọi thay đổi
- Test trước khi deploy

## 🆘 Support

- Check logs trong N8N
- Check Supabase logs
- Review error messages
- Test từng bước riêng lẻ

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-01-22
**Version**: 1.0.0

# 🚀 Workflow Hoàn Chỉnh - Crawl & Import Supabase

## 📋 Tổng quan

Workflow đầy đủ từ crawl links → crawl documents → transform → import Supabase

```
┌─────────────────────────────────────────┐
│ BƯỚC 1: Crawl Links                     │
│ → data/links.json                       │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ BƯỚC 2: Crawl Documents                 │
│ → data/result.json                      │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ BƯỚC 3: Transform                       │
│ → data/result_supabase.json             │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ BƯỚC 4: Import to Supabase              │
│ ✓ doc_urls                              │
│ ✓ doc_metadata (with versioning)       │
│ ✓ relationships                         │
│ ✓ doc_files                             │
└─────────────────────────────────────────┘
```

## 🔧 Setup Ban Đầu

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Tạo file .env

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
```

### 3. Chạy schema SQL trong Supabase

```bash
# Copy nội dung từ supabase_schema.sql
# Paste vào Supabase SQL Editor và Execute
```

### 4. Login để lấy session (nếu cần)

```powershell
python -m tvpl_crawler login-playwright `
  --login-url "https://thuvienphapluat.vn/" `
  --user-selector "#usernameTextBox" `
  --pass-selector "#passwordTextBox" `
  --submit-selector "#loginButton" `
  --cookies-out data\cookies.json `
  --headed
```

## 🎯 Chạy Workflow Đầy Đủ

### BƯỚC 1: Crawl Links

Crawl danh sách URLs từ trang tìm kiếm:

```powershell
# Crawl 5 pages đầu tiên của năm 2025
python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" `
  -o data/links.json `
  -m 5
```

**Output**: `data/links.json` với format:
```json
[
  {
    "Stt": 1,
    "Url": "https://thuvienphapluat.vn/van-ban/...",
    "Ten van ban": "Nghị định 257/2025/NĐ-CP..."
  }
]
```

### BƯỚC 2: Crawl Documents

Crawl chi tiết từng văn bản:

```powershell
python crawl_data_fast.py data/links.json data/result.json
```

**Output**: `data/result.json` với format:
```json
[
  {
    "url": "https://...",
    "doc_info": {
      "Số hiệu": "257/2025/NĐ-CP",
      "Loại văn bản": "Nghị định",
      ...
    },
    "tab4": {
      "relations": {
        "Văn bản được hướng dẫn": [...],
        "Văn bản hướng dẫn": [...]
      }
    },
    "tab8": {
      "links": [
        {"text": "Tải về PDF", "href": "..."}
      ]
    }
  }
]
```

### BƯỚC 3: Transform

Transform sang format Supabase:

```powershell
python supabase_transform.py data/result.json
```

**Output**: `data/result_supabase.json` với format:
```json
{
  "doc_metadata": [
    {
      "url": "...",
      "doc_id": "677890",
      "so_hieu": "257/2025/NĐ-CP",
      "content_hash": "abc123...",
      ...
    }
  ],
  "relationships": [...],
  "doc_files": [...]
}
```

### BƯỚC 4: Import to Supabase

Import vào Supabase với version checking:

```powershell
python import_full_supabase.py
```

**Kết quả**:
```
Importing to Supabase...

[1/3] Importing metadata...
  Inserted: 45, Skipped: 5

[2/3] Importing relationships...
  Inserted: 123

[3/3] Importing files...
  Inserted: 45

Done!
```

## 🔄 Chạy Lại với Dữ Liệu Mới

### Crawl thêm pages

```powershell
# Crawl pages 6-10
python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" `
  -o data/links_new.json `
  --start-page 6 `
  --end-page 10

# Crawl documents
python crawl_data_fast.py data/links_new.json data/result_new.json

# Transform
python supabase_transform.py data/result_new.json

# Import (sẽ tự động skip duplicate hoặc tạo version mới)
python import_full_supabase.py
```

## 📊 Kiểm Tra Dữ Liệu

### 1. Check tổng số documents

```sql
SELECT 
    status, 
    COUNT(*) as total
FROM doc_urls 
GROUP BY status;
```

### 2. Check documents mới nhất

```sql
SELECT 
    du.url,
    dm.so_hieu,
    dm.loai_van_ban,
    dm.version,
    dm.created_at
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
ORDER BY dm.created_at DESC
LIMIT 10;
```

### 3. Check documents có nhiều versions

```sql
SELECT 
    du.url,
    dm.so_hieu,
    COUNT(*) as total_versions
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
GROUP BY du.url, dm.so_hieu
HAVING COUNT(*) > 1
ORDER BY total_versions DESC;
```

### 4. Check relationships

```sql
SELECT 
    relationship_type,
    COUNT(*) as total
FROM relationships
GROUP BY relationship_type
ORDER BY total DESC;
```

### 5. Check files

```sql
SELECT 
    file_type,
    COUNT(*) as total
FROM doc_files
GROUP BY file_type;
```

## 🐛 Troubleshooting

### Lỗi: "File not found"

```powershell
# Kiểm tra file có tồn tại không
dir data\result_supabase.json
```

### Lỗi: "Supabase connection failed"

```powershell
# Kiểm tra .env file
type .env

# Test connection
python verify_supabase.py
```

### Lỗi: "Duplicate key violation"

→ Bình thường! Trigger sẽ tự động tạo version mới

### Lỗi: "Session expired"

```powershell
# Re-login
python -m tvpl_crawler login-playwright --cookies-out data\cookies.json --headed
```

## 🎯 Tips & Best Practices

### 1. Crawl từng batch nhỏ

```powershell
# Thay vì crawl 100 pages một lúc, chia nhỏ:
# Batch 1: pages 1-10
# Batch 2: pages 11-20
# ...
```

### 2. Backup trước khi import

```powershell
# Backup database
# Trong Supabase Dashboard → Database → Backups
```

### 3. Monitor logs

```powershell
# Check logs trong quá trình crawl
# Nếu có lỗi, dừng lại và fix
```

### 4. Test với dữ liệu nhỏ trước

```powershell
# Test với 1-2 documents trước
python -m tvpl_crawler links-basic -u "..." -o data/test_links.json -m 1
python crawl_data_fast.py data/test_links.json data/test_result.json
python supabase_transform.py data/test_result.json
python import_full_supabase.py
```

## 📈 Performance

- **Crawl links**: ~100 URLs/5 pages trong ~30s
- **Crawl documents**: ~10 docs/batch trong ~2-3 phút (concurrency=2)
- **Transform**: Instant
- **Import**: ~50 docs trong ~10s

## 🔐 Security

- ✅ Không commit `.env` file
- ✅ Dùng Supabase RLS (Row Level Security)
- ✅ Rotate credentials định kỳ
- ✅ Monitor failed attempts

## 📚 Tài Liệu Liên Quan

- [README_N8N.md](README_N8N.md) - Setup N8N workflow
- [N8N_SETUP_GUIDE.md](N8N_SETUP_GUIDE.md) - Chi tiết N8N
- [VERSIONING_SUMMARY.md](VERSIONING_SUMMARY.md) - Hiểu về versioning
- [QUICKSTART.md](QUICKSTART.md) - Setup nhanh 10 phút

## 🎉 Hoàn Thành!

Sau khi chạy xong workflow, bạn sẽ có:

✅ Danh sách URLs trong `doc_urls`
✅ Metadata đầy đủ trong `doc_metadata` (với versioning)
✅ Quan hệ giữa văn bản trong `relationships`
✅ Thông tin files trong `doc_files`

Sẵn sàng để tích hợp với N8N! 🚀

# 📁 File Storage Guide - Lưu Files vào Supabase

## 📋 Hiện Trạng

Hiện tại bảng `doc_files` **CHỈ LƯU METADATA**, không lưu file thật:

```sql
SELECT * FROM doc_files LIMIT 1;
```

| id | doc_metadata_id | file_name | file_type | local_path | file_size |
|----|-----------------|-----------|-----------|------------|-----------|
| 1  | 123             | Tải về PDF | pdf      | https://thuvienphapluat.vn/... | NULL |

→ `local_path` là **URL gốc**, không phải file đã download

## 🎯 2 Options

### Option 1: Chỉ Lưu URL (Hiện Tại) ✅

**Ưu điểm:**
- ✅ Nhanh, không tốn storage
- ✅ Không cần download
- ✅ Link trực tiếp đến nguồn

**Nhược điểm:**
- ❌ Phụ thuộc vào website gốc
- ❌ Link có thể bị hỏng
- ❌ Không kiểm soát được file

**Khi nào dùng:**
- Chỉ cần metadata
- Không cần lưu trữ lâu dài
- Tiết kiệm storage

### Option 2: Download và Upload lên Supabase Storage 🚀

**Ưu điểm:**
- ✅ Kiểm soát hoàn toàn file
- ✅ Không phụ thuộc nguồn gốc
- ✅ Có thể serve file nhanh hơn
- ✅ Backup an toàn

**Nhược điểm:**
- ❌ Tốn storage (cần trả phí nếu nhiều)
- ❌ Mất thời gian download/upload
- ❌ Cần xử lý lỗi download

**Khi nào dùng:**
- Cần lưu trữ lâu dài
- Muốn kiểm soát file
- Có budget cho storage

## 🚀 Setup Supabase Storage (Option 2)

### Bước 1: Tạo Bucket

1. Vào Supabase Dashboard
2. Storage → Create Bucket
3. Tên: `documents`
4. Public: ✅ (nếu muốn public) hoặc ❌ (private)

### Bước 2: Setup Policy

```sql
-- Allow public read
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'documents');

-- Allow authenticated upload
CREATE POLICY "Authenticated upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'documents' AND auth.role() = 'authenticated');
```

### Bước 3: Chạy Download Script

```powershell
python download_and_upload_files.py
```

**Output:**
```
🔍 Finding files to download...
   Found: 50 files

📥 Downloading and uploading...

  Processing: Tải về PDF
  ✅ Uploaded to: https://xxx.supabase.co/storage/v1/object/public/documents/file_abc123.pdf

  Processing: Tải về DOCX
  ✅ Uploaded to: https://xxx.supabase.co/storage/v1/object/public/documents/file_def456.docx

📊 SUMMARY:
   Total: 50
   Success: 48
   Failed: 2
```

### Bước 4: Verify

```sql
-- Check files đã upload
SELECT 
    file_name,
    file_type,
    file_size,
    local_path
FROM doc_files
WHERE local_path LIKE '%supabase.co%'
LIMIT 10;
```

## 📊 So Sánh Storage

### Option 1: Chỉ URL

```
doc_files table:
├── file_name: "Tải về PDF"
├── file_type: "pdf"
└── local_path: "https://thuvienphapluat.vn/..." ← URL gốc
```

### Option 2: Supabase Storage

```
doc_files table:
├── file_name: "Tải về PDF"
├── file_type: "pdf"
├── local_path: "https://xxx.supabase.co/storage/..." ← Supabase URL
└── file_size: 1234567

Supabase Storage:
└── documents/
    ├── file_abc123.pdf ← File thật
    ├── file_def456.docx
    └── ...
```

## 🔄 Workflow với Storage

### Workflow 1: Chỉ Metadata (Hiện Tại)

```powershell
# Import metadata + URL
python import_full_supabase.py

# Done! Không cần download
```

### Workflow 2: Download và Upload

```powershell
# Bước 1: Import metadata + URL
python import_full_supabase.py

# Bước 2: Download và upload files
python download_and_upload_files.py

# Bước 3: Verify
python -c "from supabase import create_client; ..."
```

### Workflow 3: Hybrid (Khuyến Nghị)

```powershell
# Import tất cả với URL
python import_full_supabase.py

# Chỉ download files quan trọng (PDF)
python download_and_upload_files.py --file-type pdf

# Hoặc download theo batch
python download_and_upload_files.py --limit 100
```

## 💰 Chi Phí Storage

### Supabase Storage Pricing

| Plan | Storage | Bandwidth | Giá |
|------|---------|-----------|-----|
| Free | 1 GB | 2 GB | $0 |
| Pro | 100 GB | 200 GB | $25/tháng |
| Team | 100 GB | 200 GB | $599/tháng |

### Ước Tính

Giả sử:
- 10,000 documents
- Mỗi file PDF ~500 KB
- Tổng: 10,000 × 0.5 MB = **5 GB**

→ Cần **Pro plan** ($25/tháng)

## 🎯 Khuyến Nghị

### Nếu Budget Thấp:
✅ **Option 1**: Chỉ lưu URL
- Đủ cho hầu hết use cases
- Tiết kiệm chi phí
- Dễ maintain

### Nếu Cần Reliability:
✅ **Option 2**: Download và upload
- Backup an toàn
- Không phụ thuộc nguồn
- Serve file nhanh hơn

### Hybrid Approach (Best):
✅ Lưu URL cho tất cả
✅ Download chỉ files quan trọng (PDF chính thức)
✅ Định kỳ check và re-download nếu link hỏng

## 🔧 Customize Download Script

### Download chỉ PDF:

```python
# Trong download_and_upload_files.py
files = supabase.table('doc_files')\
    .select('id, file_name, file_type, local_path')\
    .like('local_path', 'http%')\
    .eq('file_type', 'pdf')\  # ← Thêm filter
    .execute()
```

### Download theo batch:

```python
# Limit 100 files mỗi lần
files = supabase.table('doc_files')\
    .select('id, file_name, file_type, local_path')\
    .like('local_path', 'http%')\
    .limit(100)\  # ← Thêm limit
    .execute()
```

### Retry failed downloads:

```python
# Download lại files failed
files = supabase.table('doc_files')\
    .select('id, file_name, file_type, local_path')\
    .like('local_path', 'http%')\
    .is_('file_size', 'null')\  # ← Files chưa có size = chưa upload
    .execute()
```

## 📚 Tài Liệu Liên Quan

- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [download_and_upload_files.py](download_and_upload_files.py) - Script download
- [import_full_supabase.py](import_full_supabase.py) - Script import

## 🎉 Kết Luận

**Hiện tại:** Bảng `doc_files` chỉ lưu URL, không lưu file thật.

**Nếu muốn lưu file thật:**
1. Setup Supabase Storage bucket
2. Chạy `python download_and_upload_files.py`
3. Files sẽ được upload và `local_path` sẽ trở thành Supabase Storage URL

**Khuyến nghị:** Bắt đầu với Option 1 (chỉ URL), sau đó nâng cấp lên Option 2 nếu cần.

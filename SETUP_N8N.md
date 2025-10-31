# 🚀 Setup N8N Workflow - Từ đầu đến cuối

## BƯỚC 1: Setup Supabase

### 1.1. Tạo project trên Supabase
- Vào https://supabase.com
- Tạo project mới
- Lưu lại: `SUPABASE_URL` và `SUPABASE_KEY`

### 1.2. Chạy schema
```bash
# Copy nội dung file supabase_schema.sql
# Paste vào Supabase SQL Editor
# Execute
```

## BƯỚC 2: Tạo script transform

### 2.1. Tạo file supabase_transform.py
```bash
# File này sẽ transform result.json → result_supabase.json
# Đã tạo sẵn
```

### 2.2. Test transform
```bash
python supabase_transform.py data/result.json
# Output: data/result_supabase.json
```

## BƯỚC 3: Setup N8N

### 3.1. Install N8N
```bash
npm install -g n8n
# hoặc
npx n8n
```

### 3.2. Tạo Supabase Credential trong N8N
- Vào N8N → Credentials → Add Credential
- Chọn "Supabase"
- Nhập URL và Key

## BƯỚC 4: Tạo N8N Workflow

### Workflow gồm 4 nodes:

#### Node 1: Schedule Trigger
- Trigger: Cron (mỗi ngày 2AM)

#### Node 2: Execute Command - Crawl Links
```bash
cd c:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
python -m tvpl_crawler links-basic "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" 5
```

#### Node 3: Execute Command - Crawl Documents
```bash
cd c:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
python crawl_data_fast.py data/links.json data/result.json
```

#### Node 4: Execute Command - Transform
```bash
cd c:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
python supabase_transform.py data/result.json
```

#### Node 5: Code Node - Import to Supabase
```javascript
// Xem file n8n_import_supabase.js
```

## BƯỚC 5: Test thủ công

### 5.1. Crawl links
```bash
python -m tvpl_crawler links-basic "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" 2
```

### 5.2. Crawl documents
```bash
python crawl_data_fast.py data/links.json data/result.json
```

### 5.3. Transform
```bash
python supabase_transform.py data/result.json
```

### 5.4. Import thủ công (test)
```bash
python test_supabase_import.py
```

## BƯỚC 6: Monitor

### 6.1. Check Supabase
```sql
-- Xem tổng số documents
SELECT COUNT(*) FROM doc_urls;

-- Xem documents mới nhất
SELECT * FROM v_document_summary ORDER BY created_at DESC LIMIT 10;

-- Xem pending downloads
SELECT * FROM v_pending_downloads LIMIT 10;
```

### 6.2. Check N8N logs
- Vào N8N → Executions
- Xem logs của từng execution

## 📁 File Structure

```
thuvienphapluat-crawler/
├── supabase_schema.sql          ✅ Schema
├── supabase_transform.py        ⏳ Cần tạo
├── n8n_import_supabase.js       ⏳ Cần tạo
├── test_supabase_import.py      ⏳ Cần tạo
├── .env                         ⏳ Cần tạo
└── data/
    ├── links.json
    ├── result.json
    └── result_supabase.json
```

## 🔑 Environment Variables (.env)

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...
```

## ✅ Checklist

- [ ] Supabase project created
- [ ] Schema executed
- [ ] supabase_transform.py created
- [ ] n8n_import_supabase.js created
- [ ] test_supabase_import.py created
- [ ] .env file created
- [ ] Test crawl links
- [ ] Test crawl documents
- [ ] Test transform
- [ ] Test import
- [ ] N8N workflow created
- [ ] N8N workflow tested
- [ ] Schedule enabled

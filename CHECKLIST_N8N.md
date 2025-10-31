# ✅ Checklist - Tích hợp N8N với Supabase

## 📋 Tổng Quan

Checklist đầy đủ để setup và chạy workflow crawl văn bản lên Supabase qua N8N.

---

## 🔧 PHẦN 1: Setup Ban Đầu

### ✅ 1.1. Cài đặt Dependencies

- [ ] Cài Python 3.11+
- [ ] Cài dependencies: `pip install -r requirements.txt`
- [ ] Cài Playwright: `playwright install chromium`
- [ ] Test Playwright: `python -m playwright --version`

### ✅ 1.2. Setup Supabase

- [ ] Tạo project trên Supabase
- [ ] Copy `SUPABASE_URL` và `SUPABASE_KEY`
- [ ] Chạy `supabase_schema.sql` trong SQL Editor
- [ ] Verify tables đã tạo:
  ```sql
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public';
  ```
- [ ] Kết quả phải có: `doc_urls`, `doc_metadata`, `relationships`, `doc_files`

### ✅ 1.3. Tạo file .env

- [ ] Tạo file `.env` trong root folder
- [ ] Thêm nội dung:
  ```env
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_KEY=eyJxxx...
  ```
- [ ] Test connection: `python verify_supabase.py`

### ✅ 1.4. Login Session (Optional)

- [ ] Chạy login script:
  ```powershell
  python -m tvpl_crawler login-playwright `
    --login-url "https://thuvienphapluat.vn/" `
    --user-selector "#usernameTextBox" `
    --pass-selector "#passwordTextBox" `
    --submit-selector "#loginButton" `
    --cookies-out data\cookies.json `
    --headed
  ```
- [ ] Verify file `data/cookies.json` đã tạo

---

## 🧪 PHẦN 2: Test Workflow Thủ Công

### ✅ 2.1. Test Crawl Links

- [ ] Chạy command:
  ```powershell
  python -m tvpl_crawler links-basic `
    -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" `
    -o data/test_links.json `
    -m 1
  ```
- [ ] Verify file `data/test_links.json` có data
- [ ] Check format JSON đúng:
  ```json
  [
    {
      "Stt": 1,
      "Url": "https://...",
      "Ten van ban": "..."
    }
  ]
  ```

### ✅ 2.2. Test Crawl Documents

- [ ] Chạy command:
  ```powershell
  python crawl_data_fast.py data/test_links.json data/test_result.json
  ```
- [ ] Verify file `data/test_result.json` có data
- [ ] Check format có đủ: `url`, `doc_info`, `tab4`, `tab8`

### ✅ 2.3. Test Transform

- [ ] Chạy command:
  ```powershell
  python supabase_transform.py data/test_result.json
  ```
- [ ] Verify file `data/test_result_supabase.json` đã tạo
- [ ] Check format có đủ: `doc_metadata`, `relationships`, `doc_files`
- [ ] Verify `content_hash` đã được tạo

### ✅ 2.4. Test Import

- [ ] Sửa `import_full_supabase.py` để đọc file test:
  ```python
  file_path = Path('data/test_result_supabase.json')
  ```
- [ ] Chạy: `python import_full_supabase.py`
- [ ] Check output:
  ```
  [1/3] Importing metadata...
    Inserted: X, Skipped: 0
  [2/3] Importing relationships...
    Inserted: X
  [3/3] Importing files...
    Inserted: X
  ```
- [ ] Verify data trong Supabase:
  ```sql
  SELECT COUNT(*) FROM doc_urls;
  SELECT COUNT(*) FROM doc_metadata;
  SELECT COUNT(*) FROM relationships;
  SELECT COUNT(*) FROM doc_files;
  ```

### ✅ 2.5. Test Versioning

- [ ] Chạy lại import: `python import_full_supabase.py`
- [ ] Check output:
  ```
  [1/3] Importing metadata...
    Inserted: 0, Skipped: X  # ✅ Phải skip vì content_hash giống
  ```
- [ ] Verify version trong DB:
  ```sql
  SELECT url, version FROM doc_metadata ORDER BY url, version;
  ```

---

## 🚀 PHẦN 3: Chạy Workflow Đầy Đủ

### ✅ 3.1. Crawl Batch Đầu Tiên

- [ ] Chạy crawl links (5-10 pages):
  ```powershell
  python -m tvpl_crawler links-basic `
    -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" `
    -o data/links.json `
    -m 5
  ```
- [ ] Check số lượng URLs: `python -c "import json; print(len(json.load(open('data/links.json'))))"`

### ✅ 3.2. Crawl Documents

- [ ] Chạy crawl documents:
  ```powershell
  python crawl_data_fast.py data/links.json data/result.json
  ```
- [ ] Monitor logs để check errors
- [ ] Check số lượng documents crawled

### ✅ 3.3. Transform

- [ ] Chạy transform:
  ```powershell
  python supabase_transform.py data/result.json
  ```
- [ ] Verify output file

### ✅ 3.4. Import

- [ ] Sửa lại `import_full_supabase.py` để đọc file chính:
  ```python
  file_path = Path('data/result_supabase.json')
  ```
- [ ] Chạy import: `python import_full_supabase.py`
- [ ] Monitor logs
- [ ] Verify data trong Supabase

### ✅ 3.5. Verify Kết Quả

- [ ] Check tổng số documents:
  ```sql
  SELECT COUNT(*) FROM doc_urls WHERE status = 'crawled';
  ```
- [ ] Check relationships:
  ```sql
  SELECT relationship_type, COUNT(*) 
  FROM relationships 
  GROUP BY relationship_type;
  ```
- [ ] Check files:
  ```sql
  SELECT file_type, COUNT(*) 
  FROM doc_files 
  GROUP BY file_type;
  ```
- [ ] Check documents mới nhất:
  ```sql
  SELECT * FROM v_document_summary 
  ORDER BY created_at DESC 
  LIMIT 10;
  ```

---

## 🤖 PHẦN 4: Setup N8N

### ✅ 4.1. Cài đặt N8N

**Option A: Docker**
- [ ] Tạo `docker-compose.yml`
- [ ] Chạy: `docker-compose up -d`
- [ ] Access: `http://localhost:5678`

**Option B: NPM**
- [ ] Cài: `npm install -g n8n`
- [ ] Chạy: `n8n start`

### ✅ 4.2. Setup Credentials

- [ ] Vào N8N → Credentials → Add Credential
- [ ] Chọn "Supabase"
- [ ] Nhập:
  - Host: `https://xxx.supabase.co`
  - Service Role Secret: `eyJxxx...`
- [ ] Test connection

### ✅ 4.3. Import Workflow

**Option A: Import JSON**
- [ ] Vào N8N → Import from File
- [ ] Chọn `n8n_complete_workflow.json`
- [ ] Configure credentials

**Option B: Tạo thủ công**
- [ ] Tạo Schedule Trigger
- [ ] Tạo Execute Command nodes
- [ ] Tạo Supabase nodes
- [ ] Connect các nodes

### ✅ 4.4. Configure Nodes

**Node 1: Crawl Links**
- [ ] Command: `python n8n_node1_get_urls.py "URL" 5`
- [ ] Working Directory: `/app` hoặc project path

**Node 2: Supabase Insert URLs**
- [ ] Table: `doc_urls`
- [ ] Operation: Upsert
- [ ] On Conflict: `url`

**Node 3: Supabase Get Pending URLs**
- [ ] Table: `doc_urls`
- [ ] Operation: Get Many
- [ ] Filters: `status = 'pending'`
- [ ] Limit: 20

**Node 4: Crawl Documents**
- [ ] Command: `python n8n_node2_crawl_docs.py data/pending_urls.json 2`

**Node 5: Supabase Insert Metadata**
- [ ] Table: `doc_metadata`
- [ ] Operation: Insert
- [ ] Map fields từ JSON

**Node 6: Supabase Insert Relationships**
- [ ] Table: `relationships`
- [ ] Operation: Insert

**Node 7: Supabase Insert Files**
- [ ] Table: `doc_files`
- [ ] Operation: Insert

### ✅ 4.5. Test Workflow

- [ ] Click "Execute Workflow"
- [ ] Check logs từng node
- [ ] Verify data trong Supabase
- [ ] Fix errors nếu có

---

## 📊 PHẦN 5: Monitoring & Maintenance

### ✅ 5.1. Setup Monitoring

- [ ] Tạo dashboard trong Supabase
- [ ] Monitor queries:
  ```sql
  -- Pending crawls
  SELECT COUNT(*) FROM doc_urls WHERE status = 'pending';
  
  -- Crawled today
  SELECT COUNT(*) FROM doc_metadata WHERE created_at > CURRENT_DATE;
  
  -- Errors
  SELECT COUNT(*) FROM doc_urls WHERE status = 'error';
  ```

### ✅ 5.2. Schedule Regular Crawls

- [ ] Set schedule trong N8N (e.g., mỗi 6h)
- [ ] Monitor execution logs
- [ ] Check for failures

### ✅ 5.3. Backup

- [ ] Setup automatic backups trong Supabase
- [ ] Backup local data files định kỳ
- [ ] Test restore process

### ✅ 5.4. Cleanup

- [ ] Xóa temp files: `data/temp_*.json`
- [ ] Archive old data
- [ ] Monitor disk space

---

## 🐛 PHẦN 6: Troubleshooting

### ✅ 6.1. Common Issues

**Session expired:**
- [ ] Re-login: `python -m tvpl_crawler login-playwright ...`

**CAPTCHA issues:**
- [ ] Giảm concurrency: `2 → 1`
- [ ] Tăng delay
- [ ] Dùng `--reuse-session`

**Supabase connection errors:**
- [ ] Check credentials
- [ ] Check network
- [ ] Check Supabase status

**Duplicate key violations:**
- [ ] Normal! Trigger sẽ handle
- [ ] Check logs để verify

### ✅ 6.2. Debug Commands

```powershell
# Check database
python check_database.py

# Verify Supabase
python verify_supabase.py

# Test single URL
python run_single_url.py "https://..."

# Check downloads
python check_downloads.py
```

---

## 🎯 PHẦN 7: Optimization

### ✅ 7.1. Performance Tuning

- [ ] Adjust concurrency (2-3 optimal)
- [ ] Batch size (10-20 URLs)
- [ ] Schedule frequency (4-6h)

### ✅ 7.2. Database Optimization

- [ ] Check indexes:
  ```sql
  SELECT * FROM pg_indexes WHERE tablename IN ('doc_urls', 'doc_metadata');
  ```
- [ ] Analyze query performance
- [ ] Vacuum database định kỳ

### ✅ 7.3. Code Optimization

- [ ] Profile slow functions
- [ ] Optimize queries
- [ ] Cache frequently accessed data

---

## 🎉 Hoàn Thành!

Sau khi hoàn thành checklist này, bạn sẽ có:

✅ Workflow tự động crawl văn bản
✅ Data được lưu trong Supabase với versioning
✅ N8N workflow chạy tự động theo schedule
✅ Monitoring và alerting
✅ Backup và recovery plan

**Next Steps:**
- [ ] Đọc [WORKFLOW_COMPLETE.md](WORKFLOW_COMPLETE.md) để hiểu chi tiết
- [ ] Đọc [IMPORT_FIX_SUMMARY.md](IMPORT_FIX_SUMMARY.md) để hiểu các fix
- [ ] Đọc [README_N8N.md](README_N8N.md) để setup N8N

---

## 📞 Support

Nếu gặp vấn đề:
1. Check logs trong N8N
2. Check Supabase logs
3. Check file documentation
4. Create GitHub issue

Good luck! 🚀

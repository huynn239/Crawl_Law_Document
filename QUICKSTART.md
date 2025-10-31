# ⚡ Quick Start - Setup trong 10 phút

## 1️⃣ Setup Supabase (3 phút)

```bash
# 1. Tạo project tại https://supabase.com
# 2. Copy URL và Key
# 3. Vào SQL Editor, paste nội dung file supabase_schema.sql
# 4. Execute
```

## 2️⃣ Setup Local (2 phút)

```bash
# Install dependencies
pip install supabase python-dotenv

# Tạo .env file
cp .env.example .env
# Edit .env với URL và Key của bạn
```

## 3️⃣ Test Workflow (5 phút)

```bash
# Bước 1: Crawl links (có sẵn)
# Cách 1: Dùng max-pages (crawl từ page 1)
python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links.json -m 2

# Cách 2: Dùng start-page và end-page (crawl từ page 5 đến 10)
python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links.json --start-page 5 --end-page 10

# Bước 2: Crawl documents (có sẵn)
python crawl_data_fast.py data/links.json data/result.json

# Bước 3: Transform (MỚI)
python supabase_transform.py data/result.json

# Bước 4: Import to Supabase (MỚI)
python test_supabase_import.py
```

## 4️⃣ Verify

```bash
# Vào Supabase Dashboard → Table Editor
# Check tables: doc_urls, doc_metadata
# Hoặc chạy query:
```

```sql
SELECT COUNT(*) FROM doc_urls;
SELECT * FROM v_document_summary LIMIT 10;
```

## 5️⃣ Setup N8N (Optional)

```bash
# Install N8N
npx n8n

# Import workflow từ file n8n_workflow.json (sẽ tạo sau)
# Hoặc tạo manual theo hướng dẫn trong SETUP_N8N.md
```

## 🎯 Kết quả mong đợi

- ✅ Supabase có data
- ✅ Versioning hoạt động (chạy lại sẽ skip nếu không đổi)
- ✅ Raw data được lưu trong JSONB
- ✅ Query nhanh với indexed fields

## 🐛 Troubleshooting

### Lỗi: "supabase module not found"
```bash
pip install supabase python-dotenv
```

### Lỗi: "Invalid API key"
```bash
# Check lại .env file
# Đảm bảo dùng anon key, không phải service_role key
```

### Lỗi: "Table does not exist"
```bash
# Chạy lại supabase_schema.sql trong SQL Editor
```

## 📚 Next Steps

- Đọc SETUP_N8N.md để setup automation
- Đọc VERSIONING_SUMMARY.md để hiểu versioning
- Customize workflow theo nhu cầu

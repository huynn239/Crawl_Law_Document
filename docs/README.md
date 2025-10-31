# thuvienphapluat-crawler

Crawler cơ bản cho thuvienphapluat.vn bằng Python.

## Tính năng
- Khởi tạo cấu trúc dự án chuẩn, dễ mở rộng.
- HTTP client với retry, timeout, headers giả lập browser.
- Parser sử dụng BeautifulSoup + lxml.
- Logging qua loguru.
- Cấu hình qua biến môi trường hoặc `.env`.

## Yêu cầu
- Python 3.10+
- PostgreSQL 13+ (cho database)
- Windows PowerShell (mặc định có sẵn)
- Docker (tuỳ chọn - cho API mode)

## Quick Start

### 1. Cài đặt môi trường
```powershell
# Tạo môi trường ảo
python -m venv .venv

# Cài đặt dependencies
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt

# Cài Playwright browsers
.\.venv\Scripts\playwright install chromium
```

### 2. Cấu hình
Tạo file `.env` (tham khảo `.env.example`):
```env
# Crawler config
BASE_URL=https://thuvienphapluat.vn
REQUEST_TIMEOUT=20
RATE_LIMIT_PER_SEC=1.0

# Database config
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tvpl_crawl
DB_USER=postgres
DB_PASSWORD=your_password

# Login credentials (cho API refresh-cookies)
TVPL_USERNAME=your_username
TVPL_PASSWORD=your_password
```

### 3. Setup Database
```powershell
# Tự động tạo database và chạy migrations
.\.venv\Scripts\python setup_database.py
```

Script sẽ tự động:
- Tạo database `tvpl_crawl` (nếu chưa có)
- Chạy `init_db.sql` (tạo tables)
- Chạy `migrate_schema.sql` (thêm session tracking)
- Chạy `fix_db_schema.sql` (thêm FK, indexes, constraints)
- Chạy `create_views.sql` (tạo 8 views tiện ích)

## CLI Commands

### 1. login-playwright - Đăng nhập và lưu session
```powershell
.\.venv\Scripts\python -m tvpl_crawler login-playwright `
  --login-url "https://thuvienphapluat.vn/" `
  --user-selector "#usernameTextBox" `
  --pass-selector "#passwordTextBox" `
  --submit-selector "#loginButton" `
  --cookies-out data\cookies.json `
  --headed
```

**Tham số:**
- `--login-url`: URL trang đăng nhập
- `--user-selector`: CSS selector của ô username
- `--pass-selector`: CSS selector của ô password
- `--submit-selector`: CSS selector của nút đăng nhập
- `--cookies-out`: Đường dẫn lưu file cookies
- `--headed`: Hiển thị browser (bỏ đi để chạy headless)


# Xóa session cũ
del data\storage_state.json

### 2. links-basic - Crawl danh sách hyperlink
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" `
  -o data\links_2025-01-15.json `
  -m 7 `
  --page-param page `
  --cookies data\cookies.json
```

**Tham số:**
- `-u, --url`: URL trang tìm kiếm
- `-o, --out`: File output lưu kết quả
- `-m, --max-pages`: Số trang tối đa crawl
- `--page-param`: Tên tham số phân trang (mặc định: "page")
- `--cookies`: Đường dẫn file cookies

**Kết quả:** File `data\links_2025-01-15.json` chứa `[{"Stt": 1, "Tên văn bản": "...", "Url": "..."}]`

### 3. crawl_data_fast.py - Crawl dữ liệu nhanh với chống CAPTCHA
```powershell
# Chế độ mặc định: Login mới mỗi batch (chống CAPTCHA tốt)
.\.venv\Scripts\python crawl_data_fast.py data\links_2025-10-14.json

# Dùng session có sẵn (nhanh hơn, ít login)
.\.venv\Scripts\python crawl_data_fast.py data\links_2025-10-14.json data\result.json 2 30000 --reuse-session

# Debug mode (hiển thị browser)
.\.venv\Scripts\python crawl_data_fast.py data\links_2025-10-14.json data\result.json 2 30000 --headed
```

**Tham số:**
- `input_file`: File chứa danh sách hyperlink (bắt buộc)
- `output_file`: File output (tuỳ chọn, mặc định: `{input}_Result.json`)
- `concurrency`: Số request đồng thời (mặc định: 2)
- `timeout_ms`: Timeout mỗi trang (mặc định: 30000ms)
- `--reuse-session`: Dùng session có sẵn từ login-playwright
- `--headed`: Hiển thị browser (debug)

**Tính năng chống CAPTCHA:**
- ✅ Login mới mỗi 15 văn bản (batch) với session riêng
- ✅ Xoay vòng User-Agent ngẫu nhiên
- ✅ Thay đổi viewport (kích thước màn hình)
- ✅ Random delay 10-20s giữa các batch
- ✅ Tự động xử lý popup GDPR consent
- ✅ Retry khi timeout hoặc session hết hạn

**Kết quả:** File JSON với schema thu gọn (doc_info, tab4, tab8, screenshots)

### 4. crawl_formulas_fast.py - Extract công thức tính toán từ tab nội dung (🆕 IMPROVED)
```powershell
# Extract công thức bằng Improved Pattern Extractor (khuyến nghị)
.\.venv\Scripts\python crawl_formulas_fast.py data\links.json data\formulas.json playwright

# Extract công thức bằng Crawl4AI + LLM (nếu có cài đặt)
.\.venv\Scripts\python crawl_formulas_fast.py data\links.json data\formulas.json crawl4ai

# Demo với nội dung mẫu (test patterns)
.\.venv\Scripts\python demo_formula_extraction.py
```

**Tham số:**
- `input_file`: File chứa danh sách URL (bắt buộc)
- `output_file`: File output (tuỳ chọn, mặc định: `{input}_formulas.json`)
- `method`: `playwright` (improved patterns) hoặc `crawl4ai` (LLM)

**🎯 Cải tiến mới:**
- ✅ **Tỷ lệ thành công:** 0% → 60-80%
- ✅ **15 patterns chuyên biệt** cho văn bản pháp luật VN
- ✅ **8+ loại công thức:** mức lương, tỷ lệ thuế, phụ cấp, lệ phí, phạt tiền...
- ✅ **Multi-layer extraction:** Pattern + Context + Confidence scoring
- ✅ **Smart deduplication:** Loại bỏ trùng lặp thông minh

**Kết quả:** File JSON với schema mở rộng chứa công thức + confidence + context

### 5. luoc-do-playwright-from-file - Crawl dữ liệu với tùy chọn nâng cao
```powershell
.\.venv\Scripts\python -m tvpl_crawler luoc-do-playwright-from-file `
  -i data\links.json `
  -o data\result.json `
  --shots data\screenshots `
  --cookies data\cookies.json `
  --relogin-on-fail `
  --timeout-ms 30000
```

**Tham số:**
- `-i, --input`: File input chứa danh sách URL
- `-o, --output`: File output
- `--shots`: Thư mục lưu screenshots
- `--cookies`: File cookies
- `--relogin-on-fail`: Tự động login lại khi session hết hạn
- `--timeout-ms`: Timeout cho mỗi trang (ms)
- `--only-tab8`: Chỉ crawl tab "Tải về"
- `--download-tab8`: Tải file từ tab8
- `--downloads-dir`: Thư mục lưu file tải về
- `--headed`: Hiển thị browser

## Quy trình crawl: Login → Crawl hyperlink → Crawl dữ liệu

### Bước 1: Đăng nhập
```powershell
.\.venv\Scripts\python -m tvpl_crawler login-playwright `
  --login-url "https://thuvienphapluat.vn/" `
  --user-selector "#usernameTextBox" `
  --pass-selector "#passwordTextBox" `
  --submit-selector "#loginButton" `
  --cookies-out data\cookies.json `
  --headed
```

### Bước 2: Crawl danh sách hyperlink
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" `
  -o data\links_2025-01-15.json `
  -m 5 `
  --page-param page `
  --cookies data\cookies.json
```

### Bước 3: Crawl dữ liệu
```powershell
# Khuyến nghị: Dùng crawl_data_fast.py với chống CAPTCHA
.\.venv\Scripts\python crawl_data_fast.py data\links_2025-01-15.json

# Hoặc dùng session có sẵn (nếu crawl ít văn bản)
.\.venv\Scripts\python crawl_data_fast.py data\links_2025-01-15.json --reuse-session
```


## Schema JSON output

Dữ liệu crawl được trả về theo cấu trúc thu gọn:
```json
{
  "stt": 1,
  "url": "...",
  "doc_info": {
    "so_hieu": "...",
    "loai_van_ban": "...",
    "linh_vuc": "...",
    "noi_ban_hanh": "...",
    "nguoi_ky": "...",
    "ngay_ban_hanh": "...",
    "ngay_hieu_luc": "...",
    "tinh_trang": "..."
  },
  "screenshots": {
    "before": "...",
    "tab4": "...",
    "tab8": "..."
  },
  "tab4": {
    "relations": { /* 14 loại quan hệ văn bản */ },
    "summary": { /* Tổng số mỗi loại */ },
    "total": 0
  },
  "tab8": {
    "links": [ /* Download links */ ]
  },
  "tab1": {
    "formulas": [
      {
        "name": "Mức lương cơ bản",
        "formula": "Mức lương cơ bản = 1.800.000 đồng/tháng",
        "description": "Mức tiền cụ thể - amount_definition",
        "context": "...ngữ cảnh xung quanh...",
        "confidence": 0.95,
        "type": "amount_definition"
      }
    ],
    "total_formulas": 1
  }
}
```

## Database

### Schema
Dự án sử dụng PostgreSQL với 4 bảng chính:

**1. crawl_sessions** - Theo dõi các phiên crawl
```sql
session_id (PK), start_time, end_time, total_docs, status, notes
```

**2. documents_finals** - Văn bản hiện tại (latest version)
```sql
doc_id (PK), url, so_hieu, loai_van_ban, noi_ban_hanh, nguoi_ky,
ngay_ban_hanh, ngay_hieu_luc, tinh_trang, linh_vuc,
update_date, content_hash, last_crawled, session_id (FK)
```

**3. document_versions** - Lịch sử thay đổi văn bản
```sql
version_id (PK), doc_id (FK), version_hash, update_date,
so_hieu, loai_van_ban, ..., created_at, session_id (FK)
```

**4. document_relations** - Quan hệ giữa các văn bản
```sql
relation_id (PK), doc_id (FK), relation_type, related_doc_id,
related_doc_title, related_doc_number, session_id (FK)
```

### Views
Dự án có 8 views tiện ích (xem `VIEWS_USAGE.md`):
- `v_sessions` - Tổng quan sessions
- `v_session_documents` - Văn bản theo session
- `v_document_history` - Lịch sử thay đổi
- `v_document_relations_summary` - Tổng hợp quan hệ
- `v_recent_changes` - Thay đổi gần đây
- `v_most_changed_documents` - Văn bản thay đổi nhiều
- `v_stats_by_type` - Thống kê theo loại
- `v_relations_detailed` - Chi tiết quan hệ

### Queries
Xem `SQL_QUERIES_CHEATSHEET.md` cho các query thường dùng:
- Tìm văn bản theo tiêu chí
- So sánh versions
- Thống kê sessions
- Phân tích quan hệ văn bản
- Maintenance queries

## Cấu trúc dự án
```
thuvienphapluat-crawler/
├─ tvpl_crawler/          # Core crawler package
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ http.py
│  ├─ parser.py
│  ├─ storage.py
│  └─ db.py              # Database operations
├─ api/                   # FastAPI service
│  └─ main.py
├─ sql/                   # Database migrations
│  ├─ init_db.sql
│  ├─ migrate_schema.sql
│  ├─ fix_db_schema.sql
│  └─ create_views.sql
├─ crawl_data_fast.py     # Main crawl script
├─ setup_database.py      # Auto database setup
├─ compact_schema.py      # Schema helper
├─ requirements.txt
├─ .env.example
├─ Dockerfile.api         # Docker for API mode
├─ SQL_QUERIES_CHEATSHEET.md
├─ VIEWS_USAGE.md
└─ README.md
```

## API mode (Docker + ngrok + n8n)

Chạy crawler như HTTP API service để tích hợp với n8n workflow. API tự động trả về schema thu gọn.

### 1. Khởi chạy API

#### Cách 1: Docker Stack (Khuyến nghị - Full stack: PostgreSQL + pgAdmin + API + n8n)
```bash
# Tạo file .env với credentials
echo "TVPL_USERNAME=your_username" > .env
echo "TVPL_PASSWORD=your_password" >> .env

# Khởi động full stack
docker-compose -f tvpl-stack.yml up -d

# Xem logs
docker-compose -f tvpl-stack.yml logs -f tvpl-api

# Dừng services
docker-compose -f tvpl-stack.yml down
```

**Services được khởi động:**
- **PostgreSQL** (port 5432): Database `tvpl_db`
- **pgAdmin** (port 8082): GUI quản lý database
- **TVPL API** (port 8000): Crawler API với auto DB setup
- **n8n** (port 5678): Workflow automation

**Tự động setup:**
- API container tự động chạy `setup_database.py` khi khởi động
- Tạo tables, indexes, foreign keys, views
- Mount `data/` để chia sẻ cookies, screenshots, downloads
- Hot-reload code khi development

#### Cách 2: Docker standalone (chỉ API, cần PostgreSQL riêng)
```bash
# Build image
docker build -f Dockerfile.api -t tvpl-crawler-api:latest .

# Run container (cần set DB_HOST trỏ đến PostgreSQL)
docker run --rm -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_NAME=tvpl_crawl \
  -e DB_USER=postgres \
  -e DB_PASSWORD=your_password \
  -v "${PWD}/data:/app/data" \
  --name tvpl-crawler-api tvpl-crawler-api:latest
```

#### Cách 3: Local (development)
```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Danh sách API Endpoints

#### GET `/health`
Kiểm tra API hoạt động
```bash
curl http://localhost:8000/health
```
Response: `{"status": "ok"}`

#### POST `/login`
Đăng nhập thủ công với username/password
```json
{
  "username": "your_username",
  "password": "your_password",
  "login_url": "https://thuvienphapluat.vn/",
  "cookies_out": "data/cookies.json",
  "user_selector": "#usernameTextBox",
  "pass_selector": "#passwordTextBox",
  "submit_selector": "#loginButton",
  "headed": false
}
```
Response: `{"ok": true, "cookies_out": "data/cookies.json"}`

#### POST `/refresh-cookies`
Refresh cookies từ biến môi trường (không gửi credentials qua HTTP)
```bash
# Set env vars trước
export TVPL_USERNAME="your_username"
export TVPL_PASSWORD="your_password"

curl -X POST http://localhost:8000/refresh-cookies
```
Response: `{"ok": true, "cookies_out": "data/cookies.json"}`

#### POST `/links-basic`
Crawl danh sách hyperlink từ trang tìm kiếm
```json
{
  "url": "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
  "max_pages": 5,
  "page_param": "page",
  "cookies": "data/cookies.json",
  "only_basic": true
}
```
Response: `[{"Stt": 1, "Tên văn bản": "...", "Url": "..."}]`

#### POST `/tab4-details`
Crawl dữ liệu đầy đủ từ danh sách URL (doc_info + tab4 + tab8)
```json
{
  "links": [
    "https://thuvienphapluat.vn/van-ban/...",
    "https://thuvienphapluat.vn/van-ban/..."
  ],
  "cookies": "data/cookies.json",
  "headed": false,
  "relogin_on_fail": true,
  "timeout_ms": 20000,
  "screenshots": true,
  "save_to_db": true
}
```

**Tham số:**
- `links`: Danh sách URL cần crawl
- `cookies`: Đường dẫn file cookies
- `headed`: Hiển thị browser (debug)
- `relogin_on_fail`: Tự động login lại khi session hết hạn
- `timeout_ms`: Timeout mỗi trang
- `screenshots`: Chụp ảnh màn hình
- `save_to_db`: **Lưu vào PostgreSQL** (mặc định: false)

Response: Mảng JSON với schema thu gọn (xem phần Schema JSON output)

#### POST `/tab8-download`
Tải file văn bản từ tab "Tải về"
```json
{
  "links": [
    "https://thuvienphapluat.vn/van-ban/..."
  ],
  "cookies": "data/cookies.json",
  "download": true,
  "minimal": true,
  "headed": false
}
```
Response: `[{"stt": 1, "ten_van_ban": "...", "download_url": "...", "saved_to": "data/downloads/..."}]`

#### POST `/extract-formulas`
Extract công thức tính toán từ tab nội dung (tab1)
```json
{
  "links": [
    "https://thuvienphapluat.vn/van-ban/..."
  ],
  "cookies": "data/cookies.json",
  "method": "playwright",
  "headed": false
}
```

**Tham số:**
- `links`: Danh sách URL cần extract công thức
- `method`: `"playwright"` (regex nhanh) hoặc `"crawl4ai"` (LLM chính xác)
- `cookies`: Đường dẫn file cookies
- `headed`: Hiển thị browser (debug)

Response: Mảng JSON chứa các công thức tìm thấy

### 3. Expose bằng ngrok (nếu n8n ở ngoài)
```bash
ngrok http 8000
```
Copy URL công khai (ví dụ: `https://abcd-xx.ngrok-free.app`) để dùng trong n8n.

### 4. Workflow n8n đầy đủ

```
┌─────────────────┐
│ Refresh Cookies │ (Tuỳ chọn - POST /refresh-cookies)
└─────────────────┘
         ↓
┌─────────────────┐
│  Links Basic   │ POST /links-basic
└─────────────────┘ Lấy danh sách URL
         ↓
┌─────────────────┐
│Split In Batches│ Chia nhỏ (10 URL/batch)
└─────────────────┘
         ↓
┌─────────────────┐
│ Tab4 Details  │ POST /tab4-details
└─────────────────┘ Crawl dữ liệu (schema thu gọn)
         ↓
┌─────────────────┐
│     Merge      │ Gộp tất cả batch
└─────────────────┘
         ↓
┌─────────────────┐
│Write to File  │ Lưu JSON
└─────────────────┘
```

#### Cấu hình n8n nodes:

**Node 1: HTTP Request - Links Basic**
- Method: POST
- URL: `https://<ngrok-host>/links-basic`
- Body:
```json
{
  "url": "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
  "max_pages": 5,
  "page_param": "page",
  "cookies": "data/cookies.json",
  "only_basic": true
}
```

**Node 2: Split In Batches**
- Batch Size: 10

**Node 3: HTTP Request - Tab4 Details**
- Method: POST
- URL: `https://<ngrok-host>/tab4-details`
- Body:
```json
{
  "links": "{{ $json.batch.map(item => item.Url) }}",
  "cookies": "data/cookies.json",
  "headed": false,
  "relogin_on_fail": true,
  "timeout_ms": 20000,
  "screenshots": true,
  "save_to_db": true
}
```

**Node 4: Merge**
- Mode: Append

**Node 5: Write Binary File**
- File Name: `result_{{ $now.format('yyyy-MM-dd') }}.json`

## Ghi chú pháp lý và đạo đức
- Tôn trọng `robots.txt` và điều khoản sử dụng của thuvienphapluat.vn.
- Thiết lập rate limit phù hợp, chỉ crawl nội dung được phép.
- Sử dụng vào mục đích hợp pháp và tuân thủ bản quyền.

## Lưu ý
- **Docker Stack (tvpl-stack.yml)**: Full stack với PostgreSQL + pgAdmin + API + n8n
  - API tự động chạy `setup_database.py` khi khởi động
  - pgAdmin: http://localhost:8082 (email: huynn239@gmail.com)
  - n8n: http://localhost:5678
  - API: http://localhost:8000/docs
- **Database**: Khi `save_to_db=true`, API tự động:
  - Tạo crawl session mới
  - Lưu documents vào `documents_finals`
  - Tạo version history trong `document_versions`
  - Lưu relations vào `document_relations`
  - Phát hiện thay đổi bằng hash + update_date
- **Thư mục `data/`**: Mount vào container để chia sẻ cookies, screenshots, downloads
- **Auto retry**: API tự động retry và relogin khi session hết hạn
- **Screenshots**: Lưu tại `data/screenshots/`
- **Downloads**: Lưu tại `data/downloads/`

## Mở rộng tiếp theo
- Thêm queue và worker (e.g. asyncio, aiohttp) cho crawl nhiều trang
- Lưu trữ dữ liệu vào SQLite/CSV/Parquet/Elasticsearch
- Tự động phát hiện và refresh session/cookies định kỳ

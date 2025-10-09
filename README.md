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
- Windows PowerShell (mặc định có sẵn)

## Cài đặt môi trường
```powershell
# Tạo môi trường ảo
python -m venv .venv

# Cài đặt dependencies mà không cần activate (khuyến nghị cho script tự động)
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Cấu hình
Tạo file `.env` (tham khảo `.env.example`):
```
BASE_URL=https://thuvienphapluat.vn
REQUEST_TIMEOUT=20
RATE_LIMIT_PER_SEC=1.0
```

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

### 2. links-basic - Crawl danh sách hyperlink
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" `
  -o data\links_2025-01-15.json `
  -m 5 `
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

### 3. crawl_data.py - Crawl dữ liệu từ hyperlink
```powershell
python crawl_data.py data\links_2025-01-15.json
```

Hoặc chỉ định tên file output:
```powershell
python crawl_data.py data\links_2025-01-15.json data\result_2025-01-15.json
```

**Tham số:**
- `input_file`: File chứa danh sách hyperlink (bắt buộc)
- `output_file`: File output (tuỳ chọn, mặc định: `{input}_Result.json`)

**Kết quả:** File JSON với schema thu gọn (doc_info, tab4, tab8, screenshots)

### 4. luoc-do-playwright-from-file - Crawl dữ liệu với tùy chọn nâng cao
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
python crawl_data.py data\links_2025-01-15.json
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
  }
}
```

## Cấu trúc dự án
```
thuvienphapluat-crawler/
├─ tvpl_crawler/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ http.py
│  ├─ parser.py
│  └─ storage.py
├─ crawl_data.py          # Script crawl dữ liệu từ file hyperlink
├─ compact_schema.py      # Helper để thu gọn schema
├─ requirements.txt
├─ .env.example
├─ .gitignore
└─ README.md
```

## API mode (Docker + ngrok + n8n)

Chạy crawler như HTTP API service để tích hợp với n8n workflow. API tự động trả về schema thu gọn.

### 1. Khởi chạy API

#### Cách 1: Docker
```bash
# Build image
docker build -f Dockerfile.api -t tvpl-crawler-api:latest .

# Run container
docker run --rm -p 8000:8000 -v "${PWD}/data:/app/data" --name tvpl-crawler-api tvpl-crawler-api:latest
```

#### Cách 2: Local
```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000
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
  "screenshots": true
}
```
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
  "timeout_ms": 20000
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
- Thư mục `data/` được mount vào container để chia sẻ cookies và file tải về
- API tự động retry và relogin khi session hết hạn
- Screenshots lưu tại `data/screenshots/`
- File tải về lưu tại `data/downloads/`

## Mở rộng tiếp theo
- Thêm queue và worker (e.g. asyncio, aiohttp) cho crawl nhiều trang
- Lưu trữ dữ liệu vào SQLite/CSV/Parquet/Elasticsearch
- Tự động phát hiện và refresh session/cookies định kỳ

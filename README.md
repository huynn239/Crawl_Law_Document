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

## Chạy thử crawl 1 URL
```powershell
.\.venv\Scripts\python -m tvpl_crawler crawl-url --url "https://thuvienphapluat.vn/van-ban/"
```

## Quy trình: Đăng nhập → Crawl hyperlink → (tuỳ chọn) Tải file từ tab8

### Step 1: Đăng nhập bằng Playwright và lưu phiên
```powershell
.\.venv\Scripts\python -m tvpl_crawler login-playwright `
  --login-url "https://thuvienphapluat.vn/" `
  --user-selector "#usernameTextBox" `
  --pass-selector "#passwordTextBox" `
  --submit-selector "#loginButton" `
  --cookies-out data\cookies.json `
  --headed

```

### Step 2A: Crawl danh sách hyperlink (giống định dạng Stt, Tên văn bản, Url)
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler links-basic `
  -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" `
  -o data\LinkTest.json `
  -m 1 `
  --page-param page `
  --cookies data\cookies.json

```

### Step 2B: Mở từng bản ghi và lấy hyperlink ở tab "Tải về" (không tải file)
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler luoc-do-playwright-from-file `
  -i data\links_p1_top2.json `
  -o data\tab8_p1_top2.json `
  --shots data\screenshots `
  --cookies data\cookies.json `
  --only-tab8 `
  --login-first `
  --relogin-on-fail `
  --tab8-minimal-out `
  --headed


```

### Step 2C: Tải file từ tab8 và xuất JSONL tối giản (stt, ten_van_ban, download_url, saved_to)
```powershell
$env:LOGURU_LEVEL="INFO"
.\.venv\Scripts\python -m tvpl_crawler luoc-do-playwright-from-file `
  -i data\links_p1_top2.json `
  -o data\tab8_p1_top2_min.json `
  --shots data\screenshots `
  --cookies data\cookies.json `
  --only-tab8 `
  --relogin-on-fail `
  --download-tab8 `
  --downloads-dir data\downloads `
  --tab8-minimal-out `
  --headed

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
├─ requirements.txt
├─ .env.example
├─ .gitignore
└─ README.md
```

## API mode (Docker + ngrok + n8n)

Bạn có thể chạy crawler như một HTTP API service để n8n gọi qua HTTP Request (ổn định, dễ quan sát, hợp với ngrok).

### 1) Build API image
```bash
docker build -f Dockerfile.api -t tvpl-crawler-api:latest .
```

### 2) Run API container
```bash
docker run --rm -p 8000:8000 -v "${PWD}/data:/app/data" --name tvpl-crawler-api tvpl-crawler-api:latest

```

- Endpoints:
  - GET `http://localhost:8000/health` → {"status":"ok"}
  - POST `http://localhost:8000/links-basic`
    - Body JSON: `{ "url": "<search-url>", "max_pages": 1, "page_param": "page", "cookies": "data/cookies.json", "only_basic": true }`
    - Trả về mảng JSON các bản ghi (Stt, Tên văn bản, Url) nếu `only_basic=true`.
  - POST `http://localhost:8000/tab8-download`
    - Body JSON: `{ "links": ["<doc-url-1>", "<doc-url-2>"], "cookies": "data/cookies.json", "download": true, "minimal": true }`
    - Trả về mảng JSON tối giản 4 trường: `stt, ten_van_ban, download_url, saved_to`.

Lưu ý: Thư mục `data/` được mount vào container để chia sẻ cookies và file tải về (`data/downloads/`).

### 3) Expose bằng ngrok (nếu n8n ở ngoài)
```bash
ngrok http 8000
```
Copy URL công khai của ngrok (ví dụ `https://abcd-xx.ngrok-free.app`) để cấu hình trong n8n.

### 4) n8n HTTP Request nodes (ví dụ)

- Node: Links Basic
  - Method: POST
  - URL: `https://<ngrok-host>/links-basic`
  - Body (JSON):
    ```json
    {
      "url": "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
      "max_pages": 1,
      "page_param": "page",
      "cookies": "data/cookies.json",
      "only_basic": true
    }
    ```
  - Response: mảng JSON; dùng tiếp trong workflow.

- Node: Tab8 Download
  - Method: POST
  - URL: `https://<ngrok-host>/tab8-download`
  - Body (JSON):
    ```json
    {
      "links": ["<doc-url-1>", "<doc-url-2>"],
      "cookies": "data/cookies.json",
      "download": true,
      "minimal": true
    }
    ```
  - Response: mảng JSON 4 trường; file tải về nằm tại `data/downloads/` trên host.

Mẹo: Dùng thêm node "Read Binary Files" để lấy `data/Result_min.json` hoặc nén `data/downloads/` trả về n8n.

## Ghi chú pháp lý và đạo đức
- Tôn trọng `robots.txt` và điều khoản sử dụng của thuvienphapluat.vn.
- Thiết lập rate limit phù hợp, chỉ crawl nội dung được phép.
- Sử dụng vào mục đích hợp pháp và tuân thủ bản quyền.

## Mở rộng tiếp theo
- Thêm queue và worker (e.g. asyncio, aiohttp) cho crawl nhiều trang.
- Lưu trữ dữ liệu vào SQLite/CSV/Parquet/Elasticsearch.
- Tự động phát hiện và refresh session/cookies nếu cần.

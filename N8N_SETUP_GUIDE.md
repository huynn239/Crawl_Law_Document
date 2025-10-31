# 🚀 N8N Workflow Setup Guide

## 📋 Tổng quan

Workflow tự động crawl dữ liệu từ thuvienphapluat.vn vào Supabase với 2 nodes chính:

1. **Node 1**: Crawl hyperlinks (danh sách URLs)
2. **Node 2**: Crawl document data (metadata + relationships + files)

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────────────────┐
│  Schedule Trigger (Every 6h)                        │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  NODE 1: Crawl Hyperlinks                           │
│  Command: python n8n_node1_get_urls.py              │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  Supabase: Insert URLs → doc_urls table             │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  Supabase: Get Pending URLs (status='pending')      │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  NODE 2: Crawl Documents                            │
│  Command: python n8n_node2_crawl_docs.py            │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  Supabase: Insert Data                              │
│  - doc_metadata                                     │
│  - relationships                                    │
│  - doc_files                                        │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  Supabase: Update doc_urls.status = 'crawled'      │
└─────────────────────────────────────────────────────┘
```

## 📦 Prerequisites

### 1. Supabase Setup

Chạy schema SQL:
```bash
# Copy nội dung từ supabase_schema.sql
# Paste vào Supabase SQL Editor và Execute
```

### 2. Login Session

Tạo session cookies:
```powershell
python -m tvpl_crawler login-playwright `
  --login-url "https://thuvienphapluat.vn/" `
  --user-selector "#usernameTextBox" `
  --pass-selector "#passwordTextBox" `
  --submit-selector "#loginButton" `
  --cookies-out data\cookies.json `
  --headed
```

### 3. Test Scripts

Test Node 1:
```powershell
python n8n_node1_get_urls.py "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" 2
```

Test Node 2:
```powershell
# Tạo file test URLs
echo '["https://thuvienphapluat.vn/van-ban/..."]' > data/test_urls.json

python n8n_node2_crawl_docs.py data/test_urls.json 2
```

## 🔧 N8N Setup

### Option 1: Import Workflow JSON

1. Mở n8n
2. Click **Import from File**
3. Chọn `n8n_complete_workflow.json`
4. Configure Supabase credentials

### Option 2: Manual Setup

#### Node 1: Execute Command
```
Command: python n8n_node1_get_urls.py "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0" 5
Working Directory: /app
```

#### Node 2: Execute Command
```
Command: python n8n_node2_crawl_docs.py data/pending_urls.json 2
Working Directory: /app
```

## 🐳 Docker Setup

### docker-compose.yml

```yaml
version: "3.8"

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - WEBHOOK_URL=http://localhost:5678/
    volumes:
      - n8n_data:/home/node/.n8n
      - ./:/app  # Mount crawler code
    networks:
      - tvpl-net

  crawler:
    build: .
    volumes:
      - ./data:/app/data
    networks:
      - tvpl-net

volumes:
  n8n_data:

networks:
  tvpl-net:
```

### Dockerfile cho crawler

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy code
COPY . .

CMD ["tail", "-f", "/dev/null"]
```

## 📊 Monitoring

### Check Supabase Tables

```sql
-- Tổng số URLs
SELECT status, COUNT(*) FROM doc_urls GROUP BY status;

-- Documents crawled hôm nay
SELECT COUNT(*) FROM doc_metadata WHERE created_at > CURRENT_DATE;

-- Relationships
SELECT relationship_type, COUNT(*) FROM relationships GROUP BY relationship_type;

-- Files
SELECT file_type, COUNT(*) FROM doc_files GROUP BY file_type;
```

### N8N Execution Logs

- Xem logs trong n8n UI
- Check file outputs: `data/n8n_*.json`

## 🔄 Workflow Customization

### Thay đổi tần suất crawl

Edit Schedule Trigger:
```json
{
  "interval": [{"field": "hours", "hoursInterval": 6}]
}
```

### Thay đổi số URLs crawl mỗi lần

Edit "Supabase: Get Pending URLs":
```sql
SELECT id, url FROM doc_urls 
WHERE status = 'pending' 
ORDER BY crawl_priority DESC 
LIMIT 20  -- Thay đổi số này
```

### Thay đổi concurrency

Edit Node 2 command:
```
python n8n_node2_crawl_docs.py data/pending_urls.json 3  # Thay 2 → 3
```

## 🐛 Troubleshooting

### Session expired

Re-login:
```powershell
python -m tvpl_crawler login-playwright --cookies-out data\cookies.json --headed
```

### CAPTCHA issues

- Giảm concurrency: `2 → 1`
- Tăng delay trong `crawl_data_fast.py`
- Dùng `--reuse-session` flag

### Supabase connection errors

Check credentials trong n8n:
- Host
- Database name
- User/Password
- Port (5432)

## 📈 Performance Tips

1. **Batch size**: Crawl 10-20 URLs mỗi lần
2. **Concurrency**: Giữ ở 2-3 để tránh CAPTCHA
3. **Schedule**: Chạy 4-6h một lần
4. **Cleanup**: Xóa temp files định kỳ

## 🔐 Security

- Không commit `.env` file
- Dùng Supabase RLS (Row Level Security)
- Rotate credentials định kỳ
- Monitor failed login attempts

## 📝 Notes

- Node 1 crawl ~100 URLs/5 pages
- Node 2 crawl ~10 docs/batch
- Mỗi doc có ~5-15 relationships
- Mỗi doc có ~3 download files

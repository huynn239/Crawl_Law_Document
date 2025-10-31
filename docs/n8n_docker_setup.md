# N8N Docker Setup - Supabase Integration

## 1. Update docker-compose

N8N đã chạy trong Docker. Cần mount thêm volumes:

```yaml
n8n:
  volumes:
    - n8n_data:/home/node/.n8n
    - ./data:/data  # ADD THIS - mount data folder
    - ./.env:/home/node/.env:ro  # ADD THIS - mount .env
```

## 2. Tạo Supabase Credential trong N8N

1. Vào http://localhost:5678
2. Settings → Credentials → Add Credential
3. Chọn "Supabase"
4. Nhập:
   - Host: `https://xxx.supabase.co`
   - Service Role Key: `eyJxxx...`

## 3. Import Workflow

1. Workflows → Import from File
2. Chọn `n8n_workflow_final.json`
3. Update paths trong Execute Command nodes:
   - Đổi `C:\Users\...` → `/data/`

## 4. Test Workflow

Click "Execute Workflow" để test.

## 5. Enable Schedule

Bật Schedule Trigger để chạy tự động.

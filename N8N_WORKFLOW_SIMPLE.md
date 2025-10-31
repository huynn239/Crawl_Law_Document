# 🤖 N8N Workflow - Simple Setup

## 📋 Workflow Overview

```
Trigger (Schedule/Manual)
    ↓
Execute Command: Crawl Links
    ↓
Execute Command: Crawl Documents
    ↓
Execute Command: Transform
    ↓
Read JSON File
    ↓
Split Into Items
    ↓
Supabase: Upsert doc_urls
    ↓
Supabase: Check latest version
    ↓
IF: Content changed?
    ↓ YES
Supabase: Insert doc_metadata
    ↓ NO
Skip
```

## 🔧 N8N Nodes Setup

### Node 1: Schedule Trigger
- **Type**: Schedule Trigger
- **Cron**: `0 2 * * *` (mỗi ngày 2AM)

### Node 2: Execute Command - Crawl Links
- **Type**: Execute Command
- **Command**: 
```bash
cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler && python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links.json --start-page 1 --end-page 5
```

### Node 3: Execute Command - Crawl Documents
- **Type**: Execute Command
- **Command**:
```bash
cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler && python crawl_data_fast.py data/links.json data/result.json
```

### Node 4: Execute Command - Transform
- **Type**: Execute Command
- **Command**:
```bash
cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler && python supabase_transform.py data/result.json
```

### Node 5: Read File
- **Type**: Read/Write Files from Disk
- **Operation**: Read from file
- **File Path**: `C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler\data\result_supabase.json`
- **Output**: JSON

### Node 6: Split Into Items
- **Type**: Item Lists
- **Operation**: Split Out Items
- **Field**: `doc_metadata`

### Node 7: Supabase - Upsert doc_urls
- **Type**: Supabase
- **Operation**: Insert
- **Table**: `doc_urls`
- **Data**:
```json
{
  "url": "={{ $json.url }}",
  "status": "crawled"
}
```
- **On Conflict**: `url` (Do Update)

### Node 8: Supabase - Get Latest Version
- **Type**: Supabase
- **Operation**: Get Many
- **Table**: `doc_metadata`
- **Filters**:
```json
{
  "doc_url_id": "={{ $('Supabase - Upsert doc_urls').item.json.id }}"
}
```
- **Sort**: `version DESC`
- **Limit**: 1

### Node 9: IF - Check Content Changed
- **Type**: IF
- **Conditions**:
```javascript
// Check if no previous version OR content_hash changed
{{ $('Supabase - Get Latest Version').item.json.length === 0 || 
   $('Supabase - Get Latest Version').item.json[0].content_hash !== $json.content_hash }}
```

### Node 10: Supabase - Insert Metadata (IF True)
- **Type**: Supabase
- **Operation**: Insert
- **Table**: `doc_metadata`
- **Data**:
```json
{
  "doc_url_id": "={{ $('Supabase - Upsert doc_urls').item.json.id }}",
  "so_hieu": "={{ $json.so_hieu }}",
  "loai_van_ban": "={{ $json.loai_van_ban }}",
  "linh_vuc": "={{ $json.linh_vuc }}",
  "noi_ban_hanh": "={{ $json.noi_ban_hanh }}",
  "nguoi_ky": "={{ $json.nguoi_ky }}",
  "ngay_ban_hanh": "={{ $json.ngay_ban_hanh }}",
  "ngay_hieu_luc": "={{ $json.ngay_hieu_luc }}",
  "tinh_trang": "={{ $json.tinh_trang }}",
  "raw_data": "={{ $json.raw_data }}",
  "content_hash": "={{ $json.content_hash }}"
}
```

### Node 11: Loop Back (Process relationships & files)
- Similar nodes for `relationships` and `doc_files`

## 🔑 Supabase Credential Setup

1. Vào N8N → Credentials → Add Credential
2. Chọn "Supabase"
3. Nhập:
   - **Host**: `https://xxx.supabase.co`
   - **Service Role Secret**: `eyJxxx...`

## 📊 Test Workflow

1. Click "Execute Workflow" trong N8N
2. Check logs từng node
3. Verify data trong Supabase

## 🎯 Simplified Version (Chỉ import, không check version)

Nếu muốn đơn giản hơn, bỏ qua version checking:

```
Read JSON → Split Items → Supabase Insert (với ON CONFLICT DO NOTHING)
```

## 📁 File cần có

- ✅ `supabase_schema.sql` - Đã chạy trong Supabase
- ✅ `data/result_supabase.json` - Output từ transform
- ✅ Supabase credentials trong N8N

## 🐛 Troubleshooting

### Lỗi: "File not found"
→ Check đường dẫn file trong Node 5

### Lỗi: "Supabase connection failed"
→ Check credentials trong N8N

### Lỗi: "Column does not exist"
→ Chạy lại `supabase_schema.sql`

## 💡 Tips

- Test với 1-2 documents trước
- Enable "Always Output Data" trong IF node
- Check execution logs trong N8N
- Monitor Supabase logs

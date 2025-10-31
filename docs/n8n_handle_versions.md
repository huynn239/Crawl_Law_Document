# 🔄 N8N Workflow - Handle Document Versions

## 📋 Logic Versioning

### Khi nào tạo version mới?

1. **Ngày cập nhật thay đổi**: `ngay_cap_nhat` mới > `ngay_cap_nhat` cũ
2. **Content hash thay đổi**: `content_hash` mới ≠ `content_hash` cũ
3. **Lần đầu crawl**: Chưa có data trong DB

### Flow trong N8N

```
[Crawl Documents]
    ↓
[Check if Changed]
    ├─ Changed → Insert new version
    └─ Not Changed → Skip or update timestamp
```

## 🔧 N8N Nodes Setup

### Node: Check Document Changed

**Type**: Code Node

```javascript
// Input: Crawled document data
const item = $input.item.json;
const url = item.url;
const ngay_cap_nhat = item.ngay_cap_nhat;
const content_hash = item.content_hash;

// Query Supabase để lấy version mới nhất
const latestDoc = await $('Supabase').getAll({
  table: 'doc_metadata',
  filters: {
    url: url
  },
  sort: {
    field: 'version',
    direction: 'DESC'
  },
  limit: 1
});

// Check if changed
let isChanged = false;
let action = 'skip';

if (latestDoc.length === 0) {
  // Lần đầu crawl
  isChanged = true;
  action = 'insert_new';
} else {
  const latest = latestDoc[0];
  
  // So sánh ngày cập nhật
  if (ngay_cap_nhat > latest.ngay_cap_nhat) {
    isChanged = true;
    action = 'insert_version';
  }
  // So sánh hash
  else if (content_hash !== latest.content_hash) {
    isChanged = true;
    action = 'insert_version';
  }
  // Không đổi
  else {
    action = 'update_timestamp';
  }
}

return {
  json: {
    ...item,
    is_changed: isChanged,
    action: action,
    previous_version: latestDoc.length > 0 ? latestDoc[0].version : 0
  }
};
```

### Node: Route by Action

**Type**: Switch Node

```javascript
// Route based on action
const action = $input.item.json.action;

return {
  insert_new: action === 'insert_new',
  insert_version: action === 'insert_version',
  update_timestamp: action === 'update_timestamp',
  skip: action === 'skip'
};
```

### Node: Insert New Version

**Type**: Supabase Insert

```javascript
// Insert với version tự động tăng (trigger sẽ handle)
{
  table: 'doc_metadata',
  data: {
    url: $input.item.json.url,
    so_hieu: $input.item.json.so_hieu,
    // ... other fields
    ngay_cap_nhat: $input.item.json.ngay_cap_nhat,
    content_hash: $input.item.json.content_hash
  }
}
```

### Node: Update Timestamp Only

**Type**: Supabase Update

```javascript
// Chỉ update timestamp, không tạo version mới
{
  table: 'doc_urls',
  filters: {
    url: $input.item.json.url
  },
  data: {
    updated_at: 'NOW()'
  }
}
```

## 📊 Monitoring Queries

### 1. Documents với nhiều versions

```sql
SELECT 
    du.url,
    dm.so_hieu,
    COUNT(*) as total_versions,
    MAX(dm.ngay_cap_nhat) as latest_update,
    MAX(dm.version) as latest_version
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
GROUP BY du.url, dm.so_hieu
HAVING COUNT(*) > 1
ORDER BY total_versions DESC;
```

### 2. Recent changes (7 ngày gần đây)

```sql
SELECT 
    du.url,
    dm.so_hieu,
    dm.version,
    dm.ngay_cap_nhat,
    dm.created_at
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE dm.created_at > NOW() - INTERVAL '7 days'
  AND dm.version > 1
ORDER BY dm.created_at DESC;
```

### 3. Documents cần re-crawl

```sql
-- Documents có ngày cập nhật cũ (>30 ngày chưa crawl lại)
SELECT 
    du.url,
    dm.so_hieu,
    dm.ngay_cap_nhat,
    du.updated_at as last_crawled,
    CURRENT_DATE - du.updated_at::date as days_since_crawl
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE du.status = 'crawled'
  AND du.updated_at < NOW() - INTERVAL '30 days'
  AND dm.version = (SELECT MAX(version) FROM doc_metadata WHERE doc_url_id = du.id)
ORDER BY du.updated_at ASC
LIMIT 100;
```

## 🔄 Re-crawl Strategy

### Strategy 1: Periodic Full Re-crawl

Mỗi 30 ngày, re-crawl tất cả documents để detect changes:

```
[Schedule: Monthly]
    ↓
[Get All URLs]
    ↓
[Crawl Documents]
    ↓
[Check Changes & Update Versions]
```

### Strategy 2: Smart Re-crawl

Chỉ re-crawl documents có khả năng thay đổi cao:

```sql
-- Priority re-crawl list
SELECT du.url, du.crawl_priority
FROM doc_urls du
JOIN doc_metadata dm ON du.id = dm.doc_url_id
WHERE 
  -- Documents mới ban hành (trong 90 ngày)
  (dm.ngay_ban_hanh > CURRENT_DATE - INTERVAL '90 days')
  OR
  -- Documents có lịch sử thay đổi nhiều
  (SELECT COUNT(*) FROM doc_metadata WHERE doc_url_id = du.id) > 2
  OR
  -- Documents chưa crawl lại lâu
  du.updated_at < NOW() - INTERVAL '60 days'
ORDER BY 
  CASE 
    WHEN dm.ngay_ban_hanh > CURRENT_DATE - INTERVAL '30 days' THEN 1
    WHEN (SELECT COUNT(*) FROM doc_metadata WHERE doc_url_id = du.id) > 2 THEN 2
    ELSE 3
  END,
  du.updated_at ASC
LIMIT 100;
```

## 📈 Performance Tips

1. **Batch checking**: Check 10-20 docs cùng lúc
2. **Cache latest versions**: Dùng Redis cache cho latest version
3. **Index optimization**: Đảm bảo có index trên `(doc_url_id, version)`
4. **Parallel processing**: Check changes song song với insert

## 🎯 Example Workflow

```json
{
  "nodes": [
    {
      "name": "Crawl Documents",
      "type": "executeCommand"
    },
    {
      "name": "Check Changed",
      "type": "code",
      "code": "// Check logic above"
    },
    {
      "name": "Route Action",
      "type": "switch"
    },
    {
      "name": "Insert New Version",
      "type": "supabase",
      "operation": "insert"
    },
    {
      "name": "Update Timestamp",
      "type": "supabase",
      "operation": "update"
    }
  ]
}
```

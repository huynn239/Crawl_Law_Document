# 🔄 N8N Workflow - Simplified & Correct

## 📋 Flow Chính Xác

```
[Schedule: Every 6h]
    ↓
[Node 1: Crawl Hyperlinks]
    Command: python n8n_node1_get_urls.py "..." 5
    Output: links.json (có ngay_cap_nhat)
    ↓
[Supabase: Insert URLs]
    INSERT INTO doc_urls (url, status='pending')
    ON CONFLICT (url) DO NOTHING
    ↓
[Supabase: Get Pending URLs]
    SELECT * FROM doc_urls 
    WHERE status='pending' 
    LIMIT 10
    ↓
[Node 2: Crawl Documents]
    Command: python n8n_node2_crawl_docs.py urls.json 2
    Output: documents.json (có metadata + relationships + files)
    ↓
[Code: Check Each Document]
    FOR EACH document:
      latest = query_latest_version(url)
      
      IF latest is NULL:
        action = "insert_new"
      ELSE IF doc.ngay_cap_nhat > latest.ngay_cap_nhat:
        action = "insert_version"
      ELSE IF doc.content_hash != latest.content_hash:
        action = "insert_version"
      ELSE:
        action = "skip"
    ↓
[Switch: Route by Action]
    ├─ insert_new → [Insert All Data]
    ├─ insert_version → [Insert All Data]
    └─ skip → [Update Timestamp Only]
    ↓
[Supabase: Update Status]
    UPDATE doc_urls SET status='crawled'
```

## 🎯 Key Points

### 1. Insert URLs - KHÔNG duplicate
```sql
INSERT INTO doc_urls (url, status)
VALUES ('https://...', 'pending')
ON CONFLICT (url) DO NOTHING;
-- Nếu URL đã tồn tại → SKIP
```

### 2. Crawl Batch - 10 URLs/lần
```sql
SELECT id, url FROM doc_urls
WHERE status = 'pending'
ORDER BY crawl_priority DESC
LIMIT 10;
```

### 3. Check Changes - CHỈ insert khi có thay đổi
```javascript
// Pseudo-code
if (isChanged) {
  // INSERT version mới
  // INSERT relationships mới
  // INSERT files mới
} else {
  // SKIP - Không insert gì
  // Chỉ update timestamp
}
```

### 4. Version Management - Tự động
```sql
-- Trigger tự động tăng version
CREATE TRIGGER auto_increment_version
BEFORE INSERT ON doc_metadata
FOR EACH ROW
EXECUTE FUNCTION auto_increment_version();
```

## 📊 N8N Nodes Detail

### Node: Check Document Changed

```javascript
const item = $input.item.json;
const url = item.url;
const ngay_cap_nhat = item.ngay_cap_nhat;
const content_hash = item.content_hash;

// Query latest version
const query = `
  SELECT ngay_cap_nhat, content_hash, version
  FROM doc_metadata dm
  JOIN doc_urls du ON dm.doc_url_id = du.id
  WHERE du.url = $1
  ORDER BY dm.version DESC
  LIMIT 1
`;

const result = await $supabase.query(query, [url]);

let action = 'skip';

if (result.length === 0) {
  // Lần đầu
  action = 'insert_new';
} else {
  const latest = result[0];
  
  // Check thay đổi
  if (ngay_cap_nhat > latest.ngay_cap_nhat || 
      content_hash !== latest.content_hash) {
    action = 'insert_version';
  }
}

return {
  json: {
    ...item,
    action: action,
    should_insert: action !== 'skip'
  }
};
```

### Node: Insert All Data (Khi có thay đổi)

```javascript
// Chỉ chạy khi should_insert = true

// 1. Insert metadata
await $supabase.insert('doc_metadata', {
  url: item.url,
  so_hieu: item.so_hieu,
  // ... other fields
  ngay_cap_nhat: item.ngay_cap_nhat,
  content_hash: item.content_hash
  // version sẽ tự động tăng bởi trigger
});

// 2. Insert relationships
for (const rel of item.relationships) {
  await $supabase.insert('relationships', rel);
}

// 3. Insert files
for (const file of item.files) {
  await $supabase.insert('doc_files', file);
}
```

### Node: Update Timestamp Only (Khi KHÔNG thay đổi)

```javascript
// Chỉ chạy khi should_insert = false

await $supabase.update('doc_urls', {
  where: { url: item.url },
  data: { updated_at: 'NOW()' }
});
```

## 🔢 Example Scenarios

### Scenario A: 100 URLs mới
```
Crawl hyperlinks → 100 URLs
Insert to doc_urls → 100 rows (status='pending')
Get pending → 10 URLs (batch 1)
Crawl documents → 10 docs
Check changes → ALL are new (action='insert_new')
Insert data → 10 metadata + relationships + files
Update status → 10 URLs (status='crawled')

Repeat 9 more times for remaining 90 URLs
```

### Scenario B: Re-crawl 100 URLs cũ
```
Crawl hyperlinks → 100 URLs
Insert to doc_urls → 0 rows (ON CONFLICT DO NOTHING)
Get pending → 0 URLs (all are 'crawled')

Manual trigger re-crawl:
  Update status → 100 URLs (status='pending')
  Get pending → 10 URLs (batch 1)
  Crawl documents → 10 docs
  Check changes:
    - 8 docs: KHÔNG đổi (action='skip')
    - 2 docs: CÓ đổi (action='insert_version')
  Insert data → 2 metadata + relationships + files
  Update status → 10 URLs (status='crawled')
```

## 📈 Performance

- **Batch size**: 10 URLs/lần
- **Concurrency**: 2 (trong crawl_data_fast.py)
- **Time per batch**: ~2-3 phút
- **Total time for 100 URLs**: ~20-30 phút

## ⚠️ Important

1. **ON CONFLICT DO NOTHING**: Không duplicate URLs
2. **Check before insert**: Chỉ insert khi có thay đổi
3. **Batch processing**: 10 URLs/lần để tránh timeout
4. **Auto-increment version**: Trigger tự động handle
5. **Update timestamp**: Luôn update để track lần crawl cuối

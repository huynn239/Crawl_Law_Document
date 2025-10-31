# 🤖 N8N Workflow Design - Production Ready

## 📊 Workflow Overview

```
┌─────────────────────────────────────────────────────────┐
│ WORKFLOW: TVPL Crawler to Supabase (Daily)             │
└─────────────────────────────────────────────────────────┘

[Schedule Trigger] (Mỗi ngày 2AM)
        ↓
[Execute: Crawl Links] (Python)
        ↓
[Execute: Crawl Documents] (Python)
        ↓
[Execute: Transform] (Python)
        ↓
[Read JSON File]
        ↓
[Split: doc_metadata] ──→ [Import Metadata Loop]
        ↓                           ↓
[Split: relationships] ──→ [Import Relationships Loop]
        ↓                           ↓
[Split: doc_files] ──────→ [Import Files Loop]
        ↓
[Notify: Slack/Email]
```

## 🔧 Node Configuration Chi Tiết

### Node 1: Schedule Trigger
```yaml
Type: Schedule Trigger
Cron: 0 2 * * *  # Mỗi ngày 2AM
```

### Node 2: Execute Command - Crawl Links
```yaml
Type: Execute Command
Command: |
  cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
  python -m tvpl_crawler links-basic \
    -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" \
    -o data/links_{{$now.format('yyyy-MM-dd')}}.json \
    --start-page 1 \
    --end-page 10
```

### Node 3: Execute Command - Crawl Documents
```yaml
Type: Execute Command
Command: |
  cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
  python crawl_data_fast.py \
    data/links_{{$now.format('yyyy-MM-dd')}}.json \
    data/result_{{$now.format('yyyy-MM-dd')}}.json
```

### Node 4: Execute Command - Transform
```yaml
Type: Execute Command
Command: |
  cd C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler
  python supabase_transform.py \
    data/result_{{$now.format('yyyy-MM-dd')}}.json
```

### Node 5: Read Binary File
```yaml
Type: Read Binary Files
File Path: C:\Users\huynn\CascadeProjects\thuvienphapluat-crawler\data\result_{{$now.format('yyyy-MM-dd')}}_supabase.json
Property Name: data
```

### Node 6: Code - Parse JSON
```javascript
const data = JSON.parse($input.first().binary.data.toString());
return [{
  json: {
    doc_metadata: data.doc_metadata,
    relationships: data.relationships,
    doc_files: data.doc_files,
    stats: {
      total_docs: data.doc_metadata.length,
      total_rels: data.relationships.length,
      total_files: data.doc_files.length
    }
  }
}];
```

### Node 7: Split Into Batches - Metadata
```yaml
Type: Split In Batches
Batch Size: 10
Field To Split Out: doc_metadata
```

### Node 8: Loop - Import Metadata
```javascript
// For each doc in batch
const doc = $json;

// 1. Upsert doc_urls
const urlResult = await $('Supabase').upsert('doc_urls', {
  url: doc.url,
  status: 'crawled'
}, { onConflict: 'url' });

const docUrlId = urlResult[0].id;

// 2. Check latest version
const latest = await $('Supabase').select('doc_metadata', {
  filters: { doc_url_id: docUrlId },
  orderBy: 'version DESC',
  limit: 1
});

// 3. Insert if changed
if (!latest.length || latest[0].content_hash !== doc.content_hash) {
  await $('Supabase').insert('doc_metadata', {
    doc_url_id: docUrlId,
    doc_id: doc.doc_id,
    con_hieu_luc: doc.con_hieu_luc,
    extra_data: doc.extra_data,
    content_hash: doc.content_hash
  });
  return { inserted: true };
} else {
  return { inserted: false, skipped: true };
}
```

### Node 9: Split Into Batches - Relationships
```yaml
Type: Split In Batches
Batch Size: 50
Field To Split Out: relationships
```

### Node 10: Loop - Import Relationships
```javascript
const rel = $json;

// Get source_doc_id
const sourceUrl = await $('Supabase').select('doc_urls', {
  filters: { url: rel.source_url },
  limit: 1
});

if (!sourceUrl.length) return { error: 'Source not found' };

const sourceMeta = await $('Supabase').select('doc_metadata', {
  filters: { doc_url_id: sourceUrl[0].id },
  orderBy: 'version DESC',
  limit: 1
});

if (!sourceMeta.length) return { error: 'Source metadata not found' };

// Get target_doc_id (optional)
let targetDocId = null;
const targetUrl = await $('Supabase').select('doc_urls', {
  filters: { url: rel.target_doc_url },
  limit: 1
});

if (targetUrl.length) {
  const targetMeta = await $('Supabase').select('doc_metadata', {
    filters: { doc_url_id: targetUrl[0].id },
    orderBy: 'version DESC',
    limit: 1
  });
  if (targetMeta.length) targetDocId = targetMeta[0].id;
}

// Insert relationship
try {
  await $('Supabase').insert('relationships', {
    source_doc_id: sourceMeta[0].id,
    target_doc_url: rel.target_doc_url,
    target_doc_id: targetDocId,
    relationship_type: rel.relationship_type
  });
  return { inserted: true };
} catch (e) {
  return { error: e.message };
}
```

### Node 11: Split Into Batches - Files
```yaml
Type: Split In Batches
Batch Size: 10
Field To Split Out: doc_files
```

### Node 12: Loop - Import Files
```javascript
const file = $json;

// Get doc_metadata_id
const docUrl = await $('Supabase').select('doc_urls', {
  filters: { url: file.source_url },
  limit: 1
});

if (!docUrl.length) return { error: 'Doc not found' };

const docMeta = await $('Supabase').select('doc_metadata', {
  filters: { doc_url_id: docUrl[0].id },
  orderBy: 'version DESC',
  limit: 1
});

if (!docMeta.length) return { error: 'Metadata not found' };

// Insert file
try {
  await $('Supabase').insert('doc_files', {
    doc_metadata_id: docMeta[0].id,
    file_name: file.file_name,
    file_type: file.file_type,
    local_path: file.file_url
  });
  return { inserted: true };
} catch (e) {
  return { error: e.message };
}
```

### Node 13: Aggregate Results
```javascript
// Tổng hợp kết quả từ các loops
const results = $input.all();

const stats = {
  metadata_inserted: results.filter(r => r.json.inserted && !r.json.error).length,
  metadata_skipped: results.filter(r => r.json.skipped).length,
  relationships_inserted: 0, // Count from relationships loop
  files_inserted: 0, // Count from files loop
  errors: results.filter(r => r.json.error).length,
  timestamp: new Date().toISOString()
};

return [{ json: stats }];
```

### Node 14: Notify - Slack/Email
```yaml
Type: Slack / Email
Message: |
  ✅ TVPL Crawler Completed
  
  📊 Statistics:
  - Metadata inserted: {{$json.metadata_inserted}}
  - Metadata skipped: {{$json.metadata_skipped}}
  - Relationships: {{$json.relationships_inserted}}
  - Files: {{$json.files_inserted}}
  - Errors: {{$json.errors}}
  
  🕐 Time: {{$json.timestamp}}
```

## 🎯 Workflow Variants

### Variant 1: Incremental Crawl (Khuyến nghị)
- Chỉ crawl 5-10 pages mỗi ngày
- Tránh overload server
- Dễ monitor và debug

### Variant 2: Full Crawl (Tuần 1 lần)
- Crawl toàn bộ database
- Chạy vào cuối tuần
- Cần nhiều thời gian hơn

### Variant 3: On-Demand (Manual)
- Trigger thủ công
- Crawl specific pages
- Dùng cho testing

## 📋 Checklist Setup N8N

- [ ] Install N8N: `npx n8n`
- [ ] Tạo Supabase Credential trong N8N
- [ ] Import workflow từ JSON
- [ ] Test từng node riêng lẻ
- [ ] Test full workflow với 1-2 pages
- [ ] Enable schedule trigger
- [ ] Setup notification (Slack/Email)
- [ ] Monitor logs

## 🔍 Monitoring & Alerts

### Metrics cần theo dõi:
- Số documents crawled/day
- Success rate (%)
- Error rate (%)
- Execution time
- Database size growth

### Alerts:
- Error rate > 10%
- Execution time > 2 hours
- No data crawled trong 2 ngày

## 🐛 Troubleshooting

### Lỗi thường gặp:
1. **Command timeout**: Tăng timeout trong Execute Command node
2. **Memory error**: Giảm batch size
3. **Duplicate key**: Bình thường, UNIQUE constraint sẽ skip
4. **Connection timeout**: Check Supabase credentials

## 📈 Optimization Tips

1. **Batch Processing**: Xử lý 10-50 items/batch
2. **Parallel Processing**: Dùng Split In Batches với parallel mode
3. **Error Handling**: Thêm Error Trigger node
4. **Retry Logic**: Config retry trong Execute Command
5. **Caching**: Cache doc_urls lookup để giảm queries

## 🎉 Next Steps

1. Test workflow với data nhỏ
2. Monitor performance
3. Optimize batch sizes
4. Add more error handling
5. Setup backup strategy

# 🔄 Schema Migration Guide

## Tổng quan

Database được tổ chức lại thành 4 schemas:
- **tvpl**: Thư viện pháp luật (documents, relations, files, versions)
- **tnpl**: Từ ngữ pháp luật (terms)
- **system**: Hệ thống (crawl_url, crawl_sessions, audit_logs)
- **views**: Các views để query dễ dàng

## Bước 1: Chạy Migration SQL

```bash
# Copy nội dung file migration_step_by_step.sql vào SQL editor và chạy
```

## Bước 2: Update Code

### Tự động (khuyến nghị):
```bash
python update_code_for_schemas.py
```

### Thủ công:

**Trước:**
```python
supabase.table('documents_finals').select('*')
supabase.table('document_relations').insert(data)
supabase.table('doc_urls').update({'status': 'completed'})
```

**Sau:**
```python
supabase.from_('tvpl.document_finals').select('*')
supabase.from_('tvpl.document_relations').insert(data)
supabase.from_('system.crawl_url').update({'status': 'completed'})
```

## Mapping đầy đủ:

| Bảng cũ | Schema mới | Bảng mới | Code mới |
|---------|------------|----------|----------|
| `documents_finals` | `tvpl` | `document_finals` | `.from_('tvpl.document_finals')` |
| `document_relations` | `tvpl` | `document_relations` | `.from_('tvpl.document_relations')` |
| `document_files` | `tvpl` | `document_files` | `.from_('tvpl.document_files')` |
| `document_versions` | `tvpl` | `document_versions` | `.from_('tvpl.document_versions')` |
| `doc_urls` | `system` | `crawl_url` | `.from_('system.crawl_url')` |
| `crawl_sessions` | `system` | `crawl_sessions` | `.from_('system.crawl_sessions')` |
| `tnpl_terms` | `tnpl` | `terms` | `.from_('tnpl.terms')` |

## Bước 3: Test

```python
# Test query
result = supabase.from_('tvpl.document_finals').select('doc_id,title').limit(5).execute()
print(result.data)

# Test insert
supabase.from_('system.crawl_url').insert({
    'url': 'test',
    'status': 'pending'
}).execute()
```

## Bước 4: Sử dụng Views (optional)

```python
# Thay vì query phức tạp, dùng views
result = supabase.from_('views.v_documents_overview').select('*').execute()
result = supabase.from_('views.v_document_relations').eq('source_doc_id', '676102').execute()
```

## Rollback (nếu cần)

```sql
-- Di chuyển ngược về public
ALTER TABLE tvpl.document_finals SET SCHEMA public;
ALTER TABLE tvpl.document_relations SET SCHEMA public;
-- ... (tương tự cho các bảng khác)
```

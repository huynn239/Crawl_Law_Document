# 🔧 Import Fix Summary - Sửa lỗi import_full_supabase.py

## ❌ Vấn Đề Trước Đây

File `import_full_supabase.py` có 3 vấn đề chính:

### 1. Sai logic query trong `import_relationships()`

**Trước:**
```python
# Sai: Dùng doc_id để query trực tiếp
source = supabase.table('doc_metadata')\
    .select('id')\
    .eq('doc_id', rel['source_doc_id'])\  # ❌ Sai
    .execute()
```

**Vấn đề:**
- `doc_id` không phải là foreign key
- Không đảm bảo lấy đúng version mới nhất
- Có thể lấy sai document nếu có nhiều versions

### 2. Sai logic query trong `import_files()`

**Trước:**
```python
# Sai: Dùng doc_id thay vì doc_url_id
doc = supabase.table('doc_metadata')\
    .select('id')\
    .eq('doc_id', file['source_doc_id'])\  # ❌ Sai
    .execute()
```

**Vấn đề:** Tương tự như trên

### 3. Thiếu error handling

**Trước:**
```python
for rel in relationships_list:
    try:
        # ... code ...
    except Exception as e:
        errors += 1  # ❌ Không log lỗi gì
```

**Vấn đề:** Không biết lỗi gì khi import fail

## ✅ Giải Pháp

### 1. Fix `import_relationships()` - Query đúng theo schema

**Sau:**
```python
def import_relationships(relationships_list):
    for rel in relationships_list:
        try:
            # ✅ Bước 1: Lấy doc_url_id từ source_url
            source_url = rel.get('source_url')
            doc_url = supabase.table('doc_urls')\
                .select('id')\
                .eq('url', source_url)\
                .execute()
            
            doc_url_id = doc_url.data[0]['id']
            
            # ✅ Bước 2: Lấy doc_metadata_id (version mới nhất)
            source = supabase.table('doc_metadata')\
                .select('id')\
                .eq('doc_url_id', doc_url_id)\
                .order('version', desc=True)\
                .limit(1)\
                .execute()
            
            source_doc_id = source.data[0]['id']
            
            # ✅ Bước 3: Tương tự cho target (optional)
            target_doc_id = None
            target_url = rel.get('target_doc_url')
            if target_url:
                # ... query tương tự ...
            
            # ✅ Bước 4: Insert relationship
            supabase.table('relationships').insert({
                'source_doc_id': source_doc_id,
                'target_doc_url': rel['target_doc_url'],
                'target_doc_id': target_doc_id,
                'relationship_type': rel['relationship_type']
            }).execute()
            
        except Exception as e:
            errors += 1
```

### 2. Fix `import_files()` - Tương tự

**Sau:**
```python
def import_files(files_list):
    for file in files_list:
        try:
            # ✅ Bước 1: Lấy doc_url_id từ source_url
            source_url = file.get('source_url')
            doc_url = supabase.table('doc_urls')\
                .select('id')\
                .eq('url', source_url)\
                .execute()
            
            doc_url_id = doc_url.data[0]['id']
            
            # ✅ Bước 2: Lấy doc_metadata_id (version mới nhất)
            doc = supabase.table('doc_metadata')\
                .select('id')\
                .eq('doc_url_id', doc_url_id)\
                .order('version', desc=True)\
                .limit(1)\
                .execute()
            
            doc_metadata_id = doc.data[0]['id']
            
            # ✅ Bước 3: Insert file
            supabase.table('doc_files').insert({
                'doc_metadata_id': doc_metadata_id,
                'file_name': file['file_name'],
                'file_type': file['file_type'],
                'local_path': file.get('file_url', '')
            }).execute()
            
        except Exception as e:
            errors += 1
```

### 3. Thêm error logging

**Sau:**
```python
def import_metadata(metadata_list):
    for doc in metadata_list:
        try:
            # ... code ...
        except Exception as e:
            print(f"  ⚠️  Error importing {doc.get('url')}: {e}")  # ✅ Log lỗi
            continue
```

## 🔍 So Sánh Schema vs Code

### Schema Supabase

```sql
-- doc_urls
CREATE TABLE doc_urls (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    doc_id TEXT,  -- Extract từ URL
    ...
);

-- doc_metadata
CREATE TABLE doc_metadata (
    id BIGSERIAL PRIMARY KEY,
    doc_url_id BIGINT REFERENCES doc_urls(id),  -- ✅ Foreign key
    doc_id TEXT,  -- Chỉ để reference, không phải FK
    version INT DEFAULT 1,
    ...
);
```

### Code Import (Đúng)

```python
# ✅ Query theo doc_url_id (foreign key)
doc_url = supabase.table('doc_urls').select('id').eq('url', url).execute()
doc_url_id = doc_url.data[0]['id']

doc_metadata = supabase.table('doc_metadata')\
    .select('id')\
    .eq('doc_url_id', doc_url_id)\  # ✅ Dùng FK
    .order('version', desc=True)\
    .limit(1)\
    .execute()
```

## 🎯 Workflow Đúng

```
1. Insert/Upsert doc_urls
   ↓ (lấy doc_url_id)
   
2. Check version mới nhất trong doc_metadata
   ↓ (so sánh content_hash)
   
3. Insert doc_metadata nếu changed
   ↓ (trigger tự tăng version)
   
4. Insert relationships
   ↓ (query doc_metadata_id từ doc_url_id)
   
5. Insert doc_files
   ↓ (query doc_metadata_id từ doc_url_id)
```

## 📊 Test Kết Quả

### Test 1: Import lần đầu

```powershell
python import_full_supabase.py
```

**Kỳ vọng:**
```
[1/3] Importing metadata...
  Inserted: 50, Skipped: 0

[2/3] Importing relationships...
  Inserted: 150

[3/3] Importing files...
  Inserted: 50
```

### Test 2: Import lại (không thay đổi)

```powershell
python import_full_supabase.py
```

**Kỳ vọng:**
```
[1/3] Importing metadata...
  Inserted: 0, Skipped: 50  # ✅ Skip vì content_hash giống

[2/3] Importing relationships...
  Inserted: 0  # ✅ Skip vì UNIQUE constraint

[3/3] Importing files...
  Inserted: 0  # ✅ Skip vì UNIQUE constraint
```

### Test 3: Import với dữ liệu thay đổi

```powershell
# Giả sử 5 documents có content_hash mới
python import_full_supabase.py
```

**Kỳ vọng:**
```
[1/3] Importing metadata...
  Inserted: 5, Skipped: 45  # ✅ Tạo version mới cho 5 docs

[2/3] Importing relationships...
  Inserted: 15  # ✅ Relationships mới cho 5 docs

[3/3] Importing files...
  Inserted: 5  # ✅ Files mới cho 5 docs
```

## 🔄 Versioning Logic

### Khi nào tạo version mới?

```python
# Check latest version
latest = supabase.table('doc_metadata')\
    .select('content_hash')\
    .eq('doc_url_id', doc_url_id)\
    .order('version', desc=True)\
    .limit(1)\
    .execute()

# Insert if changed
if not latest.data or latest.data[0]['content_hash'] != doc['content_hash']:
    # ✅ Tạo version mới
    supabase.table('doc_metadata').insert({...}).execute()
    # Trigger sẽ tự động set version = max(version) + 1
```

### Trigger trong Supabase

```sql
CREATE OR REPLACE FUNCTION auto_increment_version()
RETURNS TRIGGER AS $$
DECLARE
    v_max_version INT;
BEGIN
    -- Lấy version cao nhất
    SELECT COALESCE(MAX(version), 0)
    INTO v_max_version
    FROM doc_metadata
    WHERE doc_url_id = NEW.doc_url_id;
    
    -- Set version mới
    NEW.version := v_max_version + 1;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 🎉 Kết Quả

Sau khi fix:

✅ Query đúng theo schema (dùng `doc_url_id` thay vì `doc_id`)
✅ Lấy đúng version mới nhất
✅ Versioning tự động hoạt động
✅ Error handling tốt hơn
✅ Không duplicate data
✅ Relationships và files link đúng với doc_metadata

## 📚 Tài Liệu Liên Quan

- [supabase_schema.sql](supabase_schema.sql) - Schema đầy đủ
- [WORKFLOW_COMPLETE.md](WORKFLOW_COMPLETE.md) - Workflow hoàn chỉnh
- [VERSIONING_SUMMARY.md](VERSIONING_SUMMARY.md) - Chi tiết về versioning

# 🔢 doc_id - Document ID Explained

## 🎯 doc_id là gì?

`doc_id` là **số định danh duy nhất** của văn bản trên website thuvienphapluat.vn, được extract từ URL.

## 📝 Format

```
URL: https://thuvienphapluat.vn/van-ban/.../Ten-van-ban-677890.aspx
                                                            ^^^^^^
                                                            doc_id
```

### Examples:

| URL | doc_id |
|-----|--------|
| `.../Quyet-dinh-3563-QD-BTC-2025-...-677890.aspx` | `677890` |
| `.../Chi-thi-32-CT-TTg-2025-...-677946.aspx` | `677946` |
| `.../Nghi-dinh-257-2025-ND-CP-...-675635.aspx?dll=true` | `675635` |

## 🔧 Extraction Methods

### Method 1: Python (trong code)
```python
import re

def extract_doc_id(url: str) -> str:
    match = re.search(r'-(\d+)\.aspx', url)
    return match.group(1) if match else None

# Example
url = "https://thuvienphapluat.vn/.../677890.aspx"
doc_id = extract_doc_id(url)  # "677890"
```

### Method 2: SQL (trong database)
```sql
CREATE FUNCTION extract_doc_id(url TEXT) RETURNS TEXT AS $$
BEGIN
    RETURN (regexp_match(url, '-(\d+)\.aspx'))[1];
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT extract_doc_id('https://thuvienphapluat.vn/.../677890.aspx');
-- Result: "677890"
```

### Method 3: JavaScript (trong n8n)
```javascript
function extractDocId(url) {
  const match = url.match(/-(\d+)\.aspx/);
  return match ? match[1] : null;
}

// Example
const url = "https://thuvienphapluat.vn/.../677890.aspx";
const docId = extractDocId(url);  // "677890"
```

## 📊 Database Schema

```sql
doc_urls (
  id BIGSERIAL PRIMARY KEY,     -- Auto-increment (1, 2, 3...)
  url TEXT UNIQUE NOT NULL,     -- Full URL
  doc_id TEXT,                  -- Extracted ID (677890)
  ...
)
```

### Tại sao có cả `id` và `doc_id`?

| Field | Purpose | Example |
|-------|---------|---------|
| `id` | Primary key trong DB (auto-increment) | 1, 2, 3, 4... |
| `doc_id` | ID từ website (để tra cứu, debug) | 677890, 677946... |
| `url` | Full URL (unique identifier thực sự) | https://... |

## 🎯 Use Cases

### 1. Debug & Logging
```python
print(f"Crawling doc_id: {doc_id}")
# Output: Crawling doc_id: 677890
```

### 2. Quick Lookup
```sql
-- Tìm document bằng doc_id (nhanh hơn search URL)
SELECT * FROM doc_urls WHERE doc_id = '677890';
```

### 3. CAPTCHA Bypass
```python
# Trong captcha_solver.py
doc_id = url.split('-')[-1].replace('.aspx', '')
if not await bypass_captcha(page, doc_id):
    raise Exception(f"CAPTCHA failed for doc_id: {doc_id}")
```

### 4. File Naming
```python
# Lưu file với doc_id
filename = f"doc_{doc_id}.pdf"
# Output: doc_677890.pdf
```

## 🔄 Auto-Extract trong DB

Trigger tự động extract doc_id khi insert:

```sql
CREATE TRIGGER trigger_auto_extract_doc_id
BEFORE INSERT OR UPDATE ON doc_urls
FOR EACH ROW
EXECUTE FUNCTION auto_extract_doc_id();
```

### Example:
```sql
-- Insert chỉ với URL
INSERT INTO doc_urls (url) 
VALUES ('https://thuvienphapluat.vn/.../677890.aspx');

-- doc_id tự động được extract
SELECT url, doc_id FROM doc_urls;
-- Result: 
-- url: https://...
-- doc_id: 677890  ← Tự động!
```

## 📈 Queries với doc_id

### Query 1: Tìm document
```sql
SELECT * FROM doc_urls WHERE doc_id = '677890';
```

### Query 2: Batch lookup
```sql
SELECT * FROM doc_urls 
WHERE doc_id IN ('677890', '677946', '675635');
```

### Query 3: Range query
```sql
-- Documents mới (doc_id lớn)
SELECT * FROM doc_urls 
WHERE doc_id::INTEGER > 677000
ORDER BY doc_id::INTEGER DESC;
```

## ⚠️ Important Notes

1. **doc_id là TEXT**: Lưu dạng string để tránh overflow
2. **Không phải unique**: Có thể có nhiều URLs khác nhau cùng doc_id (rare)
3. **Nullable**: Một số URLs đặc biệt có thể không có doc_id
4. **Auto-extract**: Trigger tự động extract, không cần manual

## 🔍 Validation

```python
def validate_doc_id(doc_id: str) -> bool:
    """Validate doc_id format"""
    if not doc_id:
        return False
    if not doc_id.isdigit():
        return False
    if len(doc_id) < 5 or len(doc_id) > 7:
        return False  # Thường 5-7 chữ số
    return True

# Examples
validate_doc_id("677890")  # True
validate_doc_id("12345")   # True
validate_doc_id("abc")     # False
validate_doc_id("")        # False
```

## 📊 Statistics

```sql
-- Phân bố doc_id
SELECT 
    SUBSTRING(doc_id, 1, 3) as prefix,
    COUNT(*) as count
FROM doc_urls
WHERE doc_id IS NOT NULL
GROUP BY prefix
ORDER BY prefix DESC;

-- Example output:
-- prefix | count
-- 677    | 150
-- 676    | 200
-- 675    | 180
```

## 🎯 Best Practices

1. **Always extract**: Luôn extract doc_id khi có URL
2. **Use for logging**: Dùng doc_id trong logs để dễ debug
3. **Index it**: Có index trên doc_id để query nhanh
4. **Validate**: Check format trước khi dùng
5. **Keep as TEXT**: Không convert sang INT để tránh issues

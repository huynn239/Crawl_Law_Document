# 📚 SQL Queries Cheatsheet - Kiểm tra văn bản

## 🎯 1. XEM DANH SÁCH SESSION

```sql
-- Xem tất cả session
SELECT 
    session_id AS "ID",
    started_at AS "Bắt đầu",
    completed_at AS "Kết thúc",
    total_docs AS "Tổng",
    new_versions AS "Thay đổi",
    unchanged_docs AS "Không đổi",
    status AS "Trạng thái"
FROM crawl_sessions
ORDER BY session_id DESC;

-- Xem session gần nhất
SELECT * FROM crawl_sessions 
ORDER BY session_id DESC LIMIT 1;

-- Xem session thành công
SELECT * FROM crawl_sessions 
WHERE status = 'COMPLETED'
ORDER BY session_id DESC;
```

---

## 📊 2. XEM VĂN BẢN THAY ĐỔI TRONG SESSION

### A. Văn bản thay đổi THỰC SỰ (có diff_summary)
```sql
-- Thay SESSION_ID = 22
SELECT 
    df.doc_id,
    df.title AS "Tên văn bản",
    df.url,
    dv.diff_summary->>'changed_fields' AS "Field thay đổi",
    (dv.diff_summary->>'relations_added')::int AS "Quan hệ thêm",
    (dv.diff_summary->>'relations_removed')::int AS "Quan hệ xóa",
    dv.crawled_at AS "Thời gian"
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id
WHERE dv.session_id = 22
  AND dv.diff_summary IS NOT NULL
ORDER BY dv.crawled_at DESC;
```

### B. Đếm số văn bản thay đổi
```sql
-- Đếm chính xác
SELECT 
    COUNT(*) FILTER (WHERE diff_summary IS NOT NULL) AS "Thay đổi thực sự",
    COUNT(*) FILTER (WHERE diff_summary IS NULL) AS "Lần đầu crawl",
    COUNT(*) AS "Tổng"
FROM document_versions
WHERE session_id = 22;
```

### C. Phân loại văn bản
```sql
SELECT 
    CASE 
        WHEN dv.diff_summary IS NOT NULL THEN 'Thay đổi thực sự'
        WHEN dv.diff_summary IS NULL THEN 'Lần đầu crawl'
    END AS "Loại",
    COUNT(*) AS "Số lượng"
FROM document_versions dv
WHERE dv.session_id = 22
GROUP BY 
    CASE 
        WHEN dv.diff_summary IS NOT NULL THEN 'Thay đổi thực sự'
        WHEN dv.diff_summary IS NULL THEN 'Lần đầu crawl'
    END;
```

---

## 🔍 3. TÌM KIẾM VĂN BẢN CỤ THỂ

```sql
-- Tìm theo doc_id
SELECT * FROM documents_finals 
WHERE doc_id = '676102';

-- Tìm theo tên văn bản
SELECT * FROM documents_finals 
WHERE title ILIKE '%quyết định%3090%';

-- Tìm theo URL
SELECT * FROM documents_finals 
WHERE url LIKE '%676102%';

-- Tìm theo số hiệu
SELECT * FROM documents_finals 
WHERE metadata->>'so_hieu' = '3090/QĐ-BKHCN';
```

---

## 📜 4. XEM LỊCH SỬ THAY ĐỔI CỦA 1 VĂN BẢN

```sql
-- Xem tất cả version của 1 văn bản
SELECT 
    dv.version_id,
    dv.crawled_at AS "Thời gian",
    cs.session_id AS "Session",
    dv.diff_summary AS "Thay đổi",
    dv.content->'doc_info' AS "Thông tin"
FROM document_versions dv
JOIN crawl_sessions cs ON dv.session_id = cs.session_id
WHERE dv.doc_id = '676102'
ORDER BY dv.crawled_at DESC;

-- So sánh 2 version gần nhất
WITH versions AS (
    SELECT 
        doc_id,
        content,
        crawled_at,
        ROW_NUMBER() OVER (PARTITION BY doc_id ORDER BY crawled_at DESC) as rn
    FROM document_versions
    WHERE doc_id = '676102'
)
SELECT 
    v1.crawled_at AS "Version mới",
    v2.crawled_at AS "Version cũ",
    v1.content->'doc_info' AS "Thông tin mới",
    v2.content->'doc_info' AS "Thông tin cũ"
FROM versions v1
LEFT JOIN versions v2 ON v1.doc_id = v2.doc_id AND v2.rn = 2
WHERE v1.rn = 1;
```

---

## 📈 5. THỐNG KÊ

```sql
-- Top 10 văn bản thay đổi nhiều nhất
SELECT 
    df.doc_id,
    df.title AS "Tên văn bản",
    COUNT(dv.version_id) AS "Số lần thay đổi",
    MAX(dv.crawled_at) AS "Lần cuối"
FROM documents_finals df
JOIN document_versions dv ON df.doc_id = dv.doc_id
WHERE dv.diff_summary IS NOT NULL
GROUP BY df.doc_id, df.title
ORDER BY COUNT(dv.version_id) DESC
LIMIT 10;

-- Thống kê theo loại văn bản
SELECT 
    metadata->>'loai_van_ban' AS "Loại văn bản",
    COUNT(*) AS "Số lượng"
FROM documents_finals
GROUP BY metadata->>'loai_van_ban'
ORDER BY COUNT(*) DESC;

-- Thống kê theo lĩnh vực
SELECT 
    metadata->>'linh_vuc' AS "Lĩnh vực",
    COUNT(*) AS "Số lượng"
FROM documents_finals
GROUP BY metadata->>'linh_vuc'
ORDER BY COUNT(*) DESC
LIMIT 10;
```

---

## 🔗 6. XEM QUAN HỆ VĂN BẢN

```sql
-- Xem quan hệ của 1 văn bản (bao gồm doc_id)
SELECT 
    dr.relation_type AS "Loại quan hệ",
    dr.target_doc_id AS "Doc ID",
    dr.target_title AS "Văn bản liên quan",
    dr.target_url AS "URL"
FROM document_relations dr
WHERE dr.source_doc_id = '676102'
ORDER BY dr.relation_type, dr.target_doc_id;

-- Đếm số quan hệ
SELECT 
    relation_type AS "Loại quan hệ",
    COUNT(*) AS "Số lượng"
FROM document_relations
WHERE source_doc_id = '676102'
GROUP BY relation_type;

-- Tìm văn bản có nhiều quan hệ nhất
SELECT 
    df.doc_id,
    df.title AS "Tên văn bản",
    COUNT(dr.id) AS "Số quan hệ"
FROM documents_finals df
JOIN document_relations dr ON df.doc_id = dr.source_doc_id
GROUP BY df.doc_id, df.title
ORDER BY COUNT(dr.id) DESC
LIMIT 10;
```

---

## 🎯 7. VIEWS CÓ SẴN (Sử dụng nhanh)

**Lưu ý:** Lệnh `\i` chỉ hoạt động trong **psql command line**. Nếu dùng pgAdmin, copy nội dung file SQL vào Query Tool.

```bash
# Trong psql command line:
psql -U tvpl_user -d tvpl_crawl
\i view_sessions.sql
SELECT * FROM sessions_view;
```

```sql
-- Hoặc chạy trực tiếp trong pgAdmin/psql:

-- Xem tất cả session (thay thế view_sessions.sql)
SELECT 
    session_id,
    started_at,
    completed_at,
    status,
    total_docs,
    new_versions,
    unchanged_docs
FROM crawl_sessions
ORDER BY session_id DESC;

-- Xem văn bản trong session (thay thế view_session_documents.sql)
SELECT 
    dv.doc_id,
    df.title,
    dv.crawled_at,
    CASE 
        WHEN dv.diff_summary IS NOT NULL THEN 'Thay đổi'
        ELSE 'Lần đầu'
    END AS "Loại"
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id
WHERE dv.session_id = 22
ORDER BY dv.crawled_at DESC;

-- Xem version của 1 văn bản (thay thế view_document_versions.sql)
SELECT 
    version_id,
    crawled_at,
    session_id,
    diff_summary,
    content->'doc_info' AS doc_info
FROM document_versions
WHERE doc_id = '676102'
ORDER BY crawled_at DESC;
```

---
```sql
-- Kiểm tra thông tin session
SELECT 
    session_id,
    total_docs AS "Tổng crawl",
    new_versions AS "Có thay đổi", 
    unchanged_docs AS "Không đổi",
    (new_versions + unchanged_docs) AS "Tổng tính"
FROM crawl_sessions
WHERE session_id = 22;
## 🔧 8. MAINTENANCE

```sql
-- Kiểm tra Foreign Keys
SELECT 
    conname AS "Constraint",
    conrelid::regclass AS "Bảng",
    confrelid::regclass AS "Tham chiếu"
FROM pg_constraint 
WHERE contype = 'f' 
AND conrelid IN ('document_versions'::regclass, 'document_relations'::regclass);

-- Kiểm tra Indexes
SELECT 
    tablename AS "Bảng",
    indexname AS "Index",
    indexdef AS "Định nghĩa"
FROM pg_indexes 
WHERE tablename IN ('documents_finals', 'document_versions', 'document_relations')
ORDER BY tablename, indexname;

-- Kiểm tra Unique Constraints
SELECT 
    conname AS "Constraint",
    conrelid::regclass AS "Bảng"
FROM pg_constraint 
WHERE contype = 'u' 
AND conrelid = 'document_versions'::regclass;

-- Kiểm tra duplicate versions (không nên có sau khi fix)
SELECT 
    doc_id,
    version_hash,
    COUNT(*) as duplicates
FROM document_versions
GROUP BY doc_id, version_hash
HAVING COUNT(*) > 1;

-- Xóa session cũ (cẩn thận! Sẽ CASCADE xóa versions)
DELETE FROM crawl_sessions WHERE session_id < 10;

-- Xóa version cũ (giữ lại 3 version gần nhất)
WITH ranked_versions AS (
    SELECT 
        version_id,
        ROW_NUMBER() OVER (PARTITION BY doc_id ORDER BY crawled_at DESC) as rn
    FROM document_versions
)
DELETE FROM document_versions
WHERE version_id IN (
    SELECT version_id FROM ranked_versions WHERE rn > 3
);

-- Xóa văn bản (CASCADE xóa versions + relations)
DELETE FROM documents_finals WHERE doc_id = '123456';

-- Vacuum database
VACUUM ANALYZE;

-- Kiểm tra kích thước database
SELECT 
    pg_size_pretty(pg_database_size('tvpl_crawl')) AS "Kích thước DB";

-- Kiểm tra kích thước bảng
SELECT 
    tablename AS "Bảng",
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS "Kích thước"
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🚀 9. QUICK COMMANDS (Copy & Paste)

```sql
-- Session gần nhất
SELECT * FROM crawl_sessions ORDER BY session_id DESC LIMIT 1;

-- Văn bản thay đổi trong session gần nhất
SELECT df.title, dv.diff_summary
FROM document_versions dv
JOIN documents_finals df ON dv.doc_id = df.doc_id
WHERE dv.session_id = (SELECT MAX(session_id) FROM crawl_sessions)
  AND dv.diff_summary IS NOT NULL;

-- Tổng số văn bản
SELECT COUNT(*) FROM documents_finals;

-- Tổng số version
SELECT COUNT(*) FROM document_versions;

-- Tổng số quan hệ
SELECT COUNT(*) FROM document_relations;
```

---

## 📝 10. EXPORT DATA

```sql
-- Export sang CSV
\copy (SELECT * FROM documents_finals) TO 'documents.csv' CSV HEADER;

-- Export văn bản thay đổi
\copy (SELECT df.doc_id, df.title, dv.diff_summary FROM document_versions dv JOIN documents_finals df ON dv.doc_id = df.doc_id WHERE dv.session_id = 22 AND dv.diff_summary IS NOT NULL) TO 'changes_session_22.csv' CSV HEADER;

-- Export JSON
SELECT json_agg(row_to_json(t))
FROM (
    SELECT * FROM documents_finals LIMIT 10
) t;
```

---

## 💡 Tips:

1. **Thay SESSION_ID**: Đổi `22` thành session bạn muốn xem
2. **Thay DOC_ID**: Đổi `'676102'` thành doc_id bạn muốn xem
3. **LIMIT**: Thêm `LIMIT 10` để xem nhanh
4. **ORDER BY**: Thêm `ORDER BY crawled_at DESC` để xem mới nhất trước
5. **ILIKE**: Dùng `ILIKE` thay vì `LIKE` để không phân biệt hoa thường

---

## 🔗 Files SQL có sẵn:

- `init_db.sql` - Khởi tạo database
- `migrate_schema.sql` - Migration schema (thêm crawl_sessions, session_id)
- `fix_db_schema.sql` - Fix schema (FK, indexes, unique constraints) ⭐ MỚI
- `view_sessions.sql` - View danh sách session
- `view_session_documents.sql` - View văn bản trong session
- `view_document_versions.sql` - View version của văn bản
- `view_version_changes.sql` - View thay đổi giữa các version
- `check_session_20.sql` - Kiểm tra session 20
- `check_duplicates.sql` - Kiểm tra duplicate versions ⭐ MỚI
- `compare_two_versions.sql` - So sánh 2 version
- `clear_data.sql` - Xóa dữ liệu

Chọn query phù hợp và thay SESSION_ID/DOC_ID! 🎯

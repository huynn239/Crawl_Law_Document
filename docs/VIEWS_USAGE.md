# 📊 Database Views - Hướng dẫn sử dụng

## 🚀 Cài đặt

```powershell
# Tạo tất cả views
psql -U tvpl_user -d tvpl_crawl -f create_views.sql

# Hoặc dùng Python
.\.venv\Scripts\python -c "import psycopg2; conn = psycopg2.connect('dbname=tvpl_crawl user=tvpl_user'); cur = conn.cursor(); cur.execute(open('create_views.sql').read()); conn.commit(); print('✓ Views created')"
```

---

## 📋 Danh sách Views

### 1. `v_sessions` - Tổng quan sessions
```sql
SELECT * FROM v_sessions LIMIT 10;
```
**Columns:**
- `session_id`, `started_at`, `completed_at`
- `duration_minutes` - Thời gian crawl (phút)
- `status`, `total_docs`, `new_versions`, `unchanged_docs`
- `change_rate_percent` - Tỷ lệ thay đổi (%)

**Use case:** Xem hiệu suất crawl, tỷ lệ thay đổi

---

### 2. `v_session_documents` - Văn bản trong session
```sql
SELECT * FROM v_session_documents 
WHERE session_id = 22 
ORDER BY crawled_at DESC;
```
**Columns:**
- `session_id`, `doc_id`, `title`, `url`, `loai_van_ban`
- `crawled_at`, `change_type` (Thay đổi/Lần đầu)
- `changed_fields`, `relations_added`, `relations_removed`

**Use case:** Xem chi tiết văn bản crawl trong 1 session

---

### 3. `v_document_history` - Lịch sử version
```sql
SELECT * FROM v_document_history 
WHERE doc_id = '676102' 
ORDER BY version_number;
```
**Columns:**
- `doc_id`, `title`, `version_id`, `crawled_at`
- `session_id`, `session_started`, `source_snapshot_date`
- `diff_summary`, `version_number` (1 = mới nhất)

**Use case:** Xem lịch sử thay đổi của 1 văn bản

---

### 4. `v_document_relations_summary` - Tổng hợp quan hệ
```sql
SELECT * FROM v_document_relations_summary 
ORDER BY total_relations DESC 
LIMIT 20;
```
**Columns:**
- `doc_id`, `title`, `loai_van_ban`
- `total_relations` - Tổng số quan hệ
- `relation_types_count` - Số loại quan hệ
- `relation_types` - Danh sách loại quan hệ
- `last_crawled`

**Use case:** Tìm văn bản có nhiều quan hệ, phân tích mạng lưới văn bản

---

### 5. `v_recent_changes` - Thay đổi gần đây
```sql
SELECT * FROM v_recent_changes 
LIMIT 50;
```
**Columns:**
- `doc_id`, `title`, `url`, `crawled_at`, `session_id`
- `changed_fields`, `relations_added`, `relations_removed`
- `source_update_date`

**Use case:** Monitor thay đổi mới nhất, dashboard

---

### 6. `v_most_changed_documents` - Top thay đổi nhiều
```sql
SELECT * FROM v_most_changed_documents 
LIMIT 20;
```
**Columns:**
- `doc_id`, `title`, `url`, `loai_van_ban`
- `version_count` - Số lần thay đổi
- `first_crawled`, `last_crawled`, `last_update_date`

**Use case:** Tìm văn bản hay thay đổi, phân tích xu hướng

---

### 7. `v_stats_by_type` - Thống kê theo loại
```sql
SELECT * FROM v_stats_by_type;
```
**Columns:**
- `loai_van_ban`
- `total_documents` - Tổng số văn bản
- `years_span` - Số năm phát hành
- `oldest_update`, `newest_update`
- `avg_relations` - Trung bình số quan hệ

**Use case:** Báo cáo tổng quan, dashboard

---

### 8. `v_relations_detailed` - Quan hệ chi tiết
```sql
SELECT * FROM v_relations_detailed 
WHERE source_doc_id = '676102';
```
**Columns:**
- `id`, `source_doc_id`, `source_title`
- `relation_type`, `target_doc_id`, `target_title`
- `target_title_from_db` - Tên từ DB (nếu đã crawl)
- `target_url`, `resolved`, `target_status` (Có trong DB/Chưa crawl)

**Use case:** Phân tích quan hệ, tìm văn bản chưa crawl

---

## 🎯 Use Cases thực tế

### Dashboard tổng quan
```sql
-- Thống kê nhanh
SELECT 
    (SELECT COUNT(*) FROM documents_finals) AS total_docs,
    (SELECT COUNT(*) FROM v_recent_changes WHERE crawled_at > NOW() - INTERVAL '7 days') AS changes_last_7days,
    (SELECT AVG(change_rate_percent) FROM v_sessions WHERE status = 'COMPLETED') AS avg_change_rate;
```

### Tìm văn bản cần crawl lại
```sql
-- Văn bản chưa crawl trong 30 ngày
SELECT doc_id, title, last_crawled 
FROM documents_finals 
WHERE last_crawled < NOW() - INTERVAL '30 days'
ORDER BY last_crawled 
LIMIT 100;
```

### Phân tích mạng lưới văn bản
```sql
-- Văn bản có nhiều quan hệ nhưng chưa crawl target
SELECT 
    vr.source_doc_id,
    vr.source_title,
    COUNT(*) FILTER (WHERE vr.target_status = 'Chưa crawl') AS uncrawled_targets
FROM v_relations_detailed vr
GROUP BY vr.source_doc_id, vr.source_title
HAVING COUNT(*) FILTER (WHERE vr.target_status = 'Chưa crawl') > 5
ORDER BY uncrawled_targets DESC;
```

### So sánh sessions
```sql
-- So sánh hiệu suất 2 sessions
SELECT 
    session_id,
    total_docs,
    new_versions,
    change_rate_percent,
    duration_minutes
FROM v_sessions
WHERE session_id IN (20, 21)
ORDER BY session_id;
```

---

## 🔧 Maintenance

### Refresh views (nếu cần)
```sql
-- Views tự động update, không cần refresh
-- Nhưng nếu muốn rebuild:
DROP VIEW IF EXISTS v_sessions CASCADE;
-- Rồi chạy lại create_views.sql
```

### Xóa tất cả views
```sql
DROP VIEW IF EXISTS v_sessions CASCADE;
DROP VIEW IF EXISTS v_session_documents CASCADE;
DROP VIEW IF EXISTS v_document_history CASCADE;
DROP VIEW IF EXISTS v_document_relations_summary CASCADE;
DROP VIEW IF EXISTS v_recent_changes CASCADE;
DROP VIEW IF EXISTS v_most_changed_documents CASCADE;
DROP VIEW IF EXISTS v_stats_by_type CASCADE;
DROP VIEW IF EXISTS v_relations_detailed CASCADE;
```

---

## 💡 Tips

1. **Performance:** Views không cache data, mỗi lần query sẽ tính lại
2. **Indexes:** Đảm bảo đã chạy `fix_db_schema.sql` để có indexes
3. **Filtering:** Luôn thêm WHERE clause để giảm data scan
4. **Materialized Views:** Nếu cần performance cao hơn, dùng MATERIALIZED VIEW

---

## 📊 Ví dụ Dashboard Query

```sql
-- Dashboard tổng quan
WITH stats AS (
    SELECT 
        COUNT(*) AS total_docs,
        MAX(last_crawled) AS last_crawl_time
    FROM documents_finals
),
recent AS (
    SELECT COUNT(*) AS changes_today
    FROM v_recent_changes
    WHERE crawled_at::date = CURRENT_DATE
),
top_types AS (
    SELECT loai_van_ban, total_documents
    FROM v_stats_by_type
    ORDER BY total_documents DESC
    LIMIT 5
)
SELECT 
    s.total_docs,
    s.last_crawl_time,
    r.changes_today,
    (SELECT json_agg(row_to_json(t)) FROM top_types t) AS top_5_types
FROM stats s, recent r;
```

Chạy `create_views.sql` để bắt đầu sử dụng! 🚀

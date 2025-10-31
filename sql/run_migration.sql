-- Chạy migration an toàn
-- Bước 1: Tạo schemas
CREATE SCHEMA IF NOT EXISTS tvpl;
CREATE SCHEMA IF NOT EXISTS tnpl;
CREATE SCHEMA IF NOT EXISTS system;

-- Bước 2: Kiểm tra tables hiện tại
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('public', 'tvpl', 'tnpl', 'system')
ORDER BY schemaname, tablename;

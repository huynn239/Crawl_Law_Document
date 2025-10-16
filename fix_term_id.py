"""Sửa term_id bị lệch - reset sequence"""
import sys
import os
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

try:
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cur = conn.cursor()
    
    print("🔧 Đang sửa term_id...\n")
    
    # Bước 1: Tạo bảng tạm với ID liên tục
    cur.execute("""
        CREATE TEMP TABLE tnpl_terms_temp AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY created_at, term_id) as new_id,
            term_name, definition, url, source_crawl, created_at, updated_at
        FROM tnpl_terms
        ORDER BY created_at, term_id;
    """)
    
    # Bước 2: Xóa bảng cũ
    cur.execute("TRUNCATE TABLE tnpl_terms RESTART IDENTITY CASCADE;")
    
    # Bước 3: Insert lại với ID mới
    cur.execute("""
        INSERT INTO tnpl_terms (term_id, term_name, definition, url, source_crawl, created_at, updated_at)
        SELECT new_id, term_name, definition, url, source_crawl, created_at, updated_at
        FROM tnpl_terms_temp
        ORDER BY new_id;
    """)
    
    # Bước 4: Reset sequence
    cur.execute("""
        SELECT setval('tnpl_terms_term_id_seq', (SELECT MAX(term_id) FROM tnpl_terms));
    """)
    
    conn.commit()
    
    # Kiểm tra
    cur.execute("SELECT MIN(term_id), MAX(term_id), COUNT(*) FROM tnpl_terms")
    min_id, max_id, count = cur.fetchone()
    
    print(f"✅ Đã sửa xong!")
    print(f"  - Min ID: {min_id}")
    print(f"  - Max ID: {max_id}")
    print(f"  - Total: {count}")
    print(f"  - ID liên tục: {min_id} → {max_id}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

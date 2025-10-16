"""Kiểm tra vị trí lưu trữ PostgreSQL"""
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
    
    # Get data directory
    cur.execute("SHOW data_directory;")
    data_dir = cur.fetchone()[0]
    print(f"📁 PostgreSQL data directory: {data_dir}")
    
    # Get database size
    cur.execute("SELECT pg_size_pretty(pg_database_size('tvpl_crawl'));")
    db_size = cur.fetchone()[0]
    print(f"💾 Database size: {db_size}")
    
    # Get table sizes
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    """)
    tables = cur.fetchall()
    
    print(f"\n📊 Table sizes:")
    for t in tables:
        print(f"  - {t[1]}: {t[2]}")
    
    # Estimate for 14,596 terms
    cur.execute("SELECT COUNT(*), pg_size_pretty(pg_total_relation_size('tnpl_terms')) FROM tnpl_terms;")
    current_count, current_size = cur.fetchone()
    
    if current_count > 0:
        estimated_size_mb = (14596 / current_count) * float(current_size.replace(' kB', '').replace(' MB', '').replace(' bytes', '')) / 1024
        print(f"\n🔮 Ước tính cho 14,596 terms:")
        print(f"  - Hiện tại: {current_count} terms = {current_size}")
        print(f"  - Dự kiến: 14,596 terms ≈ {estimated_size_mb:.1f} MB")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

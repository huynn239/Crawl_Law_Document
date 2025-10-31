"""Kiểm tra database tvpl_crawl"""
import os
import sys
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
    
    print("✅ Kết nối database thành công!\n")
    
    # Kiểm tra tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f"📊 Tables ({len(tables)}):")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t[0]}")
        count = cur.fetchone()[0]
        print(f"  - {t[0]}: {count:,} records")
    
    # Kiểm tra views
    cur.execute("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    views = cur.fetchall()
    print(f"\n👁️  Views ({len(views)}):")
    for v in views:
        print(f"  - {v[0]}")
    
    # Thống kê sessions
    cur.execute("""
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
            COUNT(*) FILTER (WHERE status = 'RUNNING') as running,
            COUNT(*) FILTER (WHERE status = 'FAILED') as failed
        FROM crawl_sessions
    """)
    stats = cur.fetchone()
    print(f"\n📈 Sessions:")
    print(f"  - Total: {stats[0]}")
    print(f"  - Completed: {stats[1]}")
    print(f"  - Running: {stats[2]}")
    print(f"  - Failed: {stats[3]}")
    
    # Session gần nhất
    cur.execute("""
        SELECT session_id, status, started_at, total_docs, new_versions, unchanged_docs
        FROM crawl_sessions
        ORDER BY started_at DESC
        LIMIT 5
    """)
    recent = cur.fetchall()
    print(f"\n🕐 5 Sessions gần nhất:")
    for r in recent:
        print(f"  #{r[0]}: {r[1]} - {r[2]} - {r[3]} docs ({r[4]} new, {r[5]} unchanged)")
    
    cur.close()
    conn.close()
    
except ImportError:
    print("❌ psycopg2 chưa cài. Chạy: pip install psycopg2-binary")
except Exception as e:
    print(f"❌ Lỗi: {e}")

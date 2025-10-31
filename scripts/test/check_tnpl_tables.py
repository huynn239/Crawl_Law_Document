"""Kiểm tra TNPL tables"""
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
    
    print("✅ Connected to database: tvpl_crawl\n")
    
    # Check TNPL tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'tnpl%'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    
    if tables:
        print(f"📊 TNPL Tables ({len(tables)}):")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t[0]}")
            count = cur.fetchone()[0]
            print(f"  - {t[0]}: {count:,} records")
    else:
        print("⚠️  Không tìm thấy TNPL tables!")
        print("Chạy: python setup_tnpl_db.py")
    
    # Show all tables
    print("\n📋 All tables in tvpl_crawl:")
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    all_tables = cur.fetchall()
    for t in all_tables:
        print(f"  - {t[0]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

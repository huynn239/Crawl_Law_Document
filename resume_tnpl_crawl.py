"""Resume TNPL crawl từ trang bị dừng"""
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
    
    # Đếm số terms hiện có
    cur.execute("SELECT COUNT(*) FROM tnpl_terms;")
    current_count = cur.fetchone()[0]
    
    # Ước tính trang đã crawl (20 terms/page)
    pages_done = current_count // 20
    
    print(f"📊 Hiện tại: {current_count} terms")
    print(f"📄 Đã crawl: ~{pages_done} trang")
    print(f"\n💡 Để tiếp tục crawl:")
    print(f"   python crawl_tnpl_to_db.py 730")
    print(f"\n   (Script tự động UPDATE nếu trùng URL)")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

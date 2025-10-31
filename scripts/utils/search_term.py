"""Tìm kiếm thuật ngữ trong database"""
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
    
    # Tìm kiếm
    search_term = "máy biến áp"
    
    cur.execute("""
        SELECT term_id, term_name, definition, url
        FROM tnpl_terms
        WHERE term_name ILIKE %s
    """, (f"%{search_term}%",))
    
    results = cur.fetchall()
    
    if results:
        print(f"🔍 Tìm thấy {len(results)} kết quả cho '{search_term}':\n")
        for r in results:
            print(f"ID: {r[0]}")
            print(f"Tên: {r[1]}")
            print(f"Định nghĩa: {r[2][:200]}...")
            print(f"URL: {r[3]}")
            print("-" * 80)
    else:
        print(f"❌ Không tìm thấy '{search_term}'")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

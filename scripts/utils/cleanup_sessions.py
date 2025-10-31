"""Cleanup các session bị treo (RUNNING nhưng đã dừng)"""
import sys
from tvpl_crawler.core.tnpl_db import TNPLDatabase
import os
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

db = TNPLDatabase(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "tvpl_crawl"),
    user=os.getenv("DB_USER", "tvpl_user"),
    password=os.getenv("DB_PASSWORD", "")
)

conn = db.connect()
cur = conn.cursor()

# Tìm các session RUNNING
cur.execute("""
    SELECT session_id, started_at, total_terms, new_terms, updated_terms
    FROM tnpl_crawl_sessions
    WHERE status = 'RUNNING'
    ORDER BY session_id
""")

sessions = cur.fetchall()

if not sessions:
    print("✅ Không có session nào bị treo")
    cur.close()
    db.close()
    exit(0)

print(f"⚠️  Tìm thấy {len(sessions)} session đang RUNNING:\n")
for s in sessions:
    print(f"  Session #{s[0]}: started at {s[1]}, total={s[2]}, new={s[3]}, updated={s[4]}")

print("\n💡 Các session này sẽ được đánh dấu COMPLETED hoặc FAILED\n")

confirm = input("Bạn có muốn cleanup? (yes/no): ")

if confirm.lower() == "yes":
    # Đánh dấu tất cả session RUNNING thành FAILED
    cur.execute("""
        UPDATE tnpl_crawl_sessions
        SET status = 'FAILED',
            completed_at = NOW(),
            notes = 'Interrupted - cleaned up by script'
        WHERE status = 'RUNNING'
    """)
    conn.commit()
    print(f"✅ Đã cleanup {len(sessions)} sessions")
else:
    print("❌ Hủy bỏ")

cur.close()
db.close()

"""Xóa dữ liệu bị lỗi (term_id >= 14521)"""
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

# Đếm số record bị lỗi
cur.execute("SELECT COUNT(*) FROM tnpl_terms WHERE term_id > 7080")
count = cur.fetchone()[0]

print(f"⚠️  Tìm thấy {count} records với term_id > 7080 (dữ liệu bị lỗi)")
print(f"📍 Các record này sẽ bị XÓA để crawl lại đúng thứ tự\n")

confirm = input("Bạn có chắc muốn xóa? (yes/no): ")

if confirm.lower() == "yes":
    cur.execute("DELETE FROM tnpl_terms WHERE term_id > 7080")
    conn.commit()
    print(f"✅ Đã xóa {count} records")
    
    # Reset sequence
    cur.execute("SELECT setval('tnpl_terms_term_id_seq', 7080, true)")
    conn.commit()
    print(f"✅ Đã reset sequence về 7081")
    print(f"💡 Bây giờ chạy: python crawl_tnpl_resume.py 355 730")
else:
    print("❌ Hủy bỏ")

cur.close()
db.close()

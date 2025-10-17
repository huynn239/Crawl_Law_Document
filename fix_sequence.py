"""Fix sequence term_id về đúng giá trị"""
import sys
from tvpl_crawler.tnpl_db import TNPLDatabase
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

# Lấy term_id lớn nhất hiện tại
cur.execute("SELECT MAX(term_id) FROM tnpl_terms")
max_id = cur.fetchone()[0]

print(f"📊 Max term_id hiện tại: {max_id}")

# Reset sequence về max_id + 1
cur.execute(f"SELECT setval('tnpl_terms_term_id_seq', {max_id}, true)")
conn.commit()

print(f"✅ Đã reset sequence về {max_id + 1}")
print(f"💡 Bây giờ INSERT mới sẽ bắt đầu từ term_id = {max_id + 1}")

cur.close()
db.close()

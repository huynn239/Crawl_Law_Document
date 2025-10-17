"""Export dữ liệu từ page 224"""
import sys
import json
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

# Lấy dữ liệu từ page 224 (20 terms/page, page 224 = term 4461-4480)
# Tính offset: (224-1) * 20 = 4460
cur.execute("""
    SELECT term_id, term_name, definition, url
    FROM tnpl_terms
    ORDER BY term_id
    LIMIT 20 OFFSET 4460
""")

rows = cur.fetchall()
terms = []

for row in rows:
    terms.append({
        "term_id": row[0],
        "term_name": row[1],
        "definition": row[2],
        "url": row[3]
    })

cur.close()
db.close()

# Lưu ra file
output_file = "data/page_224_export.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(terms, f, ensure_ascii=False, indent=2)

print(f"✅ Exported {len(terms)} terms from page 224 to {output_file}")

# In ra màn hình để kiểm tra
for term in terms:
    print(f"\n[{term['term_id']}] {term['term_name']}")
    print(f"    URL: {term['url']}")
    print(f"    Definition: {term['definition'][:100]}...")

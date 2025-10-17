"""Export TNPL terms từ database ra JSON"""
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

# Lấy tất cả terms
cur.execute("""
    SELECT term_id, term_name, definition, url, source_crawl, created_at, updated_at
    FROM tnpl_terms
    ORDER BY term_id
""")

rows = cur.fetchall()
terms = []

for row in rows:
    terms.append({
        "term_id": row[0],
        "term_name": row[1],
        "definition": row[2],
        "url": row[3],
        "source_crawl": row[4],
        "created_at": row[5].isoformat() if row[5] else None,
        "updated_at": row[6].isoformat() if row[6] else None
    })

cur.close()
db.close()

# Lưu ra file
output_file = "data/tnpl_terms_export.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(terms, f, ensure_ascii=False, indent=2)

print(f"✅ Exported {len(terms)} terms to {output_file}")

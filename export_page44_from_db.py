"""Export page 44 data từ database"""
import sys
import os
import json
from dotenv import load_dotenv
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "tvpl_crawl"),
    user=os.getenv("DB_USER", "tvpl_user"),
    password=os.getenv("DB_PASSWORD", "")
)
cur = conn.cursor()

# Page 44 = records 861-880 (20 terms per page)
start_id = (44 - 1) * 20 + 1  # 861
end_id = 44 * 20  # 880

cur.execute("""
    SELECT term_id, term_name, definition, url
    FROM tnpl_terms
    WHERE term_id >= %s AND term_id <= %s
    ORDER BY term_id
""", (start_id, end_id))

terms = []
for row in cur.fetchall():
    terms.append({
        "term_id": row[0],
        "term_name": row[1],
        "definition": row[2],
        "url": row[3]
    })

output_file = "data/page44_from_db.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(terms, f, ensure_ascii=False, indent=2)

print(f"✅ Exported {len(terms)} terms from page 44")
print(f"📁 File: {output_file}")
print(f"📊 IDs: {start_id} → {end_id}")

cur.close()
conn.close()

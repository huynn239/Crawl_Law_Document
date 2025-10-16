import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "tvpl_crawl"),
    user=os.getenv("DB_USER", "tvpl_user"),
    password=os.getenv("DB_PASSWORD", "")
)

cur = conn.cursor()
cur.execute("DROP TRIGGER IF EXISTS trg_update_relations_summary ON document_relations;")
cur.execute("DROP FUNCTION IF EXISTS update_relations_summary();")
conn.commit()
print("Trigger dropped")
conn.close()

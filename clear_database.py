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

print("Xoa toan bo data...")
cur.execute("TRUNCATE TABLE document_relations CASCADE;")
cur.execute("TRUNCATE TABLE document_versions CASCADE;")
cur.execute("TRUNCATE TABLE documents_finals CASCADE;")
cur.execute("TRUNCATE TABLE crawl_sessions RESTART IDENTITY CASCADE;")

conn.commit()
print("Da xoa toan bo data")
conn.close()

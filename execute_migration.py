import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
conn.autocommit = True
cur = conn.cursor()

# Tạo schemas
print("Tạo schemas...")
cur.execute("CREATE SCHEMA IF NOT EXISTS tvpl;")
cur.execute("CREATE SCHEMA IF NOT EXISTS tnpl;")
cur.execute("CREATE SCHEMA IF NOT EXISTS system;")
print("✓ Schemas đã tạo")

# Kiểm tra tables
print("\nKiểm tra tables hiện tại:")
cur.execute("""
    SELECT schemaname, tablename 
    FROM pg_tables 
    WHERE schemaname IN ('public', 'tvpl', 'tnpl', 'system')
    ORDER BY schemaname, tablename;
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}")

# Chạy migration
print("\nChạy migration...")
with open('migrate_to_schemas.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
    cur.execute(sql)
print("✓ Migration hoàn tất")

cur.close()
conn.close()

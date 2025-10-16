"""Setup TNPL database tables"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 chưa cài. Chạy: pip install psycopg2-binary")
    sys.exit(1)

def main():
    print("🚀 Setup TNPL database...\n")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "tvpl_crawl"),
            user=os.getenv("DB_USER", "tvpl_user"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cur = conn.cursor()
        
        # Run SQL file
        sql_file = Path("sql/init_tnpl_db.sql")
        if sql_file.exists():
            sql = sql_file.read_text(encoding='utf-8')
            cur.execute(sql)
            conn.commit()
            print("✓ Created tables: tnpl_terms, tnpl_crawl_sessions")
        else:
            print("⚠ sql/init_tnpl_db.sql not found")
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('tnpl_terms', 'tnpl_crawl_sessions')")
        count = cur.fetchone()[0]
        
        print(f"\n✅ Setup complete! ({count} tables)")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

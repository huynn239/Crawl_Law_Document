"""Auto setup database khi chạy lần đầu"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ psycopg2 chưa cài. Chạy: pip install psycopg2-binary")
    sys.exit(1)

def run_sql_file(cursor, filepath):
    """Chạy file SQL"""
    sql = Path(filepath).read_text(encoding='utf-8')
    cursor.execute(sql)
    print(f"  ✓ {filepath}")

def main():
    print("🚀 Auto setup database...\n")
    
    # 1. Kết nối postgres để tạo database
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname="postgres",
            user=os.getenv("DB_USER", "tvpl_user"),
            password=os.getenv("DB_PASSWORD", "")
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Tạo database nếu chưa có
        db_name = os.getenv("DB_NAME", "tvpl_crawl")
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"✓ Created database: {db_name}")
        else:
            print(f"ℹ Database {db_name} already exists")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        print("ℹ Make sure PostgreSQL is running and credentials are correct in .env")
        sys.exit(1)
    
    # 2. Kết nối database vừa tạo
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=db_name,
            user=os.getenv("DB_USER", "tvpl_user"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cur = conn.cursor()
        
        # 3. Chạy các file SQL theo thứ tự
        print("\n📊 Running SQL scripts...")
        
        sql_files = [
            "init_db.sql",
            "migrate_schema.sql",
            "fix_db_schema.sql",
            "create_views.sql"
        ]
        
        for sql_file in sql_files:
            if Path(sql_file).exists():
                try:
                    run_sql_file(cur, sql_file)
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠ {sql_file}: {e}")
                    conn.rollback()
            else:
                print(f"  ⚠ {sql_file} not found")
        
        # 4. Verify
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public'")
        view_count = cur.fetchone()[0]
        
        print(f"\n✅ Setup complete!")
        print(f"  - Tables: {table_count}")
        print(f"  - Views: {view_count}")
        print(f"\n📖 Next steps:")
        print(f"  1. Update .env with your credentials")
        print(f"  2. Read README.md for usage")
        print(f"  3. Run: python -m tvpl_crawler login-playwright")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not Path(".env").exists():
        print("⚠️ .env file not found!")
        print("Copy .env.example to .env and update credentials")
        sys.exit(1)
    main()

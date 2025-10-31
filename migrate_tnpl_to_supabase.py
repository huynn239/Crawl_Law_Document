# -*- coding: utf-8 -*-
"""Migrate TNPL data from local PostgreSQL to Supabase"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
import psycopg2

load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Local PostgreSQL connection
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DB = os.getenv('PG_DATABASE', 'tvpl_crawler')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD')

if not PG_PASSWORD:
    print("⚠️  Thiếu PG_PASSWORD trong .env")
    print("Nhập password PostgreSQL:")
    PG_PASSWORD = input("> ")

def create_supabase_tables():
    """Tạo bảng TNPL trên Supabase (chạy SQL trực tiếp)"""
    print("📋 Tạo bảng TNPL trên Supabase...")
    
    sql = """
    -- Table: tnpl_terms
    CREATE TABLE IF NOT EXISTS tnpl_terms (
        term_id SERIAL PRIMARY KEY,
        term_name VARCHAR(500) NOT NULL,
        definition TEXT,
        url VARCHAR(1000) UNIQUE NOT NULL,
        source_crawl VARCHAR(500),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- Table: tnpl_crawl_sessions
    CREATE TABLE IF NOT EXISTS tnpl_crawl_sessions (
        session_id SERIAL PRIMARY KEY,
        started_at TIMESTAMP DEFAULT NOW(),
        completed_at TIMESTAMP,
        total_terms INTEGER DEFAULT 0,
        new_terms INTEGER DEFAULT 0,
        updated_terms INTEGER DEFAULT 0,
        status VARCHAR(20) DEFAULT 'RUNNING',
        notes TEXT
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_tnpl_terms_name ON tnpl_terms(term_name);
    CREATE INDEX IF NOT EXISTS idx_tnpl_terms_created ON tnpl_terms(created_at DESC);
    """
    
    print("\n⚠️  BẠN CẦN CHẠY SQL SAU TRÊN SUPABASE SQL EDITOR:")
    print("="*60)
    print(sql)
    print("="*60)
    print("\nSau khi chạy SQL xong, nhấn Enter để tiếp tục...")
    input()

def migrate_tnpl_terms():
    """Migrate bảng tnpl_terms"""
    print("\n📦 Đang migrate bảng tnpl_terms...")
    
    # Connect to local PostgreSQL
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        print(f"✓ Kết nối PostgreSQL thành công: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    except Exception as e:
        print(f"✗ Lỗi kết nối PostgreSQL: {e}")
        print(f"\nKiểm tra lại:")
        print(f"  - Host: {PG_HOST}")
        print(f"  - Port: {PG_PORT}")
        print(f"  - Database: {PG_DB}")
        print(f"  - User: {PG_USER}")
        print(f"  - Password: {'***' if PG_PASSWORD else '(empty)'}")
        sys.exit(1)
    cursor = conn.cursor()
    
    # Lấy tất cả dữ liệu
    cursor.execute("SELECT term_id, term_name, definition, url, source_crawl, created_at, updated_at FROM tnpl_terms ORDER BY term_id")
    rows = cursor.fetchall()
    
    print(f"✓ Tìm thấy {len(rows)} thuật ngữ trong PostgreSQL local")
    
    # Insert vào Supabase (batch 100 records)
    batch_size = 100
    total_inserted = 0
    total_skipped = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        data = []
        
        for row in batch:
            data.append({
                'term_name': row[1],
                'definition': row[2],
                'url': row[3],
                'source_crawl': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            })
        
        try:
            result = supabase.from_('tnpl.terms').insert(data).execute()
            total_inserted += len(data)
            print(f"  ✓ Inserted batch {i//batch_size + 1}: {len(data)} records")
        except Exception as e:
            error_msg = str(e)
            if 'duplicate key' in error_msg.lower():
                print(f"  ⚠ Batch {i//batch_size + 1}: Duplicate URLs, skipping...")
                total_skipped += len(data)
            else:
                print(f"  ✗ Batch {i//batch_size + 1} error: {error_msg[:100]}")
                total_skipped += len(data)
    
    cursor.close()
    conn.close()
    
    print(f"\n✓ Migrate tnpl_terms hoàn tất:")
    print(f"  - Inserted: {total_inserted}")
    print(f"  - Skipped: {total_skipped}")

def migrate_tnpl_sessions():
    """Migrate bảng tnpl_crawl_sessions"""
    print("\n📦 Đang migrate bảng tnpl_crawl_sessions...")
    
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
    except Exception as e:
        print(f"✗ Lỗi kết nối PostgreSQL: {e}")
        return
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_id, started_at, completed_at, total_terms, 
               new_terms, updated_terms, status, notes 
        FROM tnpl_crawl_sessions ORDER BY session_id
    """)
    rows = cursor.fetchall()
    
    print(f"✓ Tìm thấy {len(rows)} sessions trong PostgreSQL local")
    
    data = []
    for row in rows:
        data.append({
            'started_at': row[1].isoformat() if row[1] else None,
            'completed_at': row[2].isoformat() if row[2] else None,
            'total_terms': row[3],
            'new_terms': row[4],
            'updated_terms': row[5],
            'status': row[6],
            'notes': row[7]
        })
    
    try:
        result = supabase.from_('tnpl.crawl_sessions').insert(data).execute()
        print(f"✓ Inserted {len(data)} sessions")
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
    
    cursor.close()
    conn.close()

def verify_migration():
    """Kiểm tra dữ liệu sau khi migrate"""
    print("\n🔍 Kiểm tra dữ liệu trên Supabase...")
    
    # Count tnpl_terms
    result = supabase.from_('tnpl.terms').select('term_id', count='exact').execute()
    terms_count = result.count
    print(f"  ✓ tnpl_terms: {terms_count} records")
    
    # Count tnpl_crawl_sessions
    result = supabase.from_('tnpl.crawl_sessions').select('session_id', count='exact').execute()
    sessions_count = result.count
    print(f"  ✓ tnpl_crawl_sessions: {sessions_count} records")
    
    # Sample data
    result = supabase.from_('tnpl.terms').select('*').limit(3).execute()
    print(f"\n📄 Sample data (3 records):")
    for term in result.data:
        print(f"  - {term['term_name'][:50]}...")

if __name__ == '__main__':
    print("="*60)
    print("MIGRATE TNPL DATA: PostgreSQL → Supabase")
    print("="*60)
    
    # Step 1: Tạo bảng trên Supabase
    create_supabase_tables()
    
    # Step 2: Migrate tnpl_terms
    migrate_tnpl_terms()
    
    # Step 3: Migrate tnpl_crawl_sessions
    migrate_tnpl_sessions()
    
    # Step 4: Verify
    verify_migration()
    
    print("\n" + "="*60)
    print("✓ MIGRATION HOÀN TẤT!")
    print("="*60)

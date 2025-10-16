"""Backup TNPL data trước khi fix"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

try:
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cur = conn.cursor()
    
    # Backup terms
    cur.execute("SELECT * FROM tnpl_terms ORDER BY term_id")
    terms = cur.fetchall()
    
    backup_data = []
    for t in terms:
        backup_data.append({
            "term_id": t[0],
            "term_name": t[1],
            "definition": t[2],
            "url": t[3],
            "source_crawl": t[4],
            "created_at": str(t[5]),
            "updated_at": str(t[6])
        })
    
    # Save backup
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"tnpl_backup_{timestamp}.json"
    
    backup_file.write_text(json.dumps(backup_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Backup thành công!")
    print(f"  - File: {backup_file}")
    print(f"  - Records: {len(backup_data)}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

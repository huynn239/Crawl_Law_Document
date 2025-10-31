# -*- coding: utf-8 -*-
"""Lưu file JSON vào database"""
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from tvpl_crawler.core.db import TVPLDatabase

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python save_to_db.py <json_file>")
    sys.exit(1)

json_file = Path(sys.argv[1])
data = json.loads(json_file.read_text(encoding="utf-8"))

db = TVPLDatabase(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "tvpl_crawl"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "")
)

db.connect()
print(f"Đang lưu {len(data)} văn bản vào database...")

session_id = db.start_crawl_session()
print(f"✓ Session #{session_id}")

new_versions = 0
unchanged = 0
errors = 0

for item in data:
    if item.get("error"):
        continue
    try:
        has_changed = db.save_document(item, session_id)
        if has_changed:
            new_versions += 1
            print(f"  ✓ {item['doc_info'].get('so_hieu', 'N/A')} - Thay đổi")
        else:
            unchanged += 1
            print(f"  - {item['doc_info'].get('so_hieu', 'N/A')} - Không đổi")
    except Exception as e:
        errors += 1
        print(f"  ✗ {item.get('url', '')}: {e}")

if errors > 0:
    db.fail_crawl_session(session_id, len(data), new_versions, unchanged, errors)
    print(f"\n✗ Hoàn tất với lỗi: {new_versions} thay đổi, {unchanged} không đổi, {errors} lỗi")
else:
    db.complete_crawl_session(session_id, len(data), new_versions, unchanged)
    print(f"\n✓ Hoàn tất: {new_versions} thay đổi, {unchanged} không đổi")

db.close()

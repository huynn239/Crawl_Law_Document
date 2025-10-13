# -*- coding: utf-8 -*-
"""Crawl dữ liệu từ file hyperlink"""
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from tvpl_crawler.playwright_extract_v2 import extract_luoc_do_with_playwright
from compact_schema import compact_schema
from tvpl_crawler.db import TVPLDatabase

load_dotenv()

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Usage: python crawl_data.py <input_file> [output_file]")
    print("Example: python crawl_data.py data/links_2025-01-15.json")
    sys.exit(1)

input_file = Path(sys.argv[1])
if len(sys.argv) >= 3:
    output_file = Path(sys.argv[2])
else:
    output_file = input_file.parent / f"{input_file.stem}_Result.json"

links = json.loads(input_file.read_text(encoding="utf-8"))
print(f"Bắt đầu crawl {len(links)} văn bản từ {input_file}...\n")

results = []
for item in links:
    stt = item["Stt"]
    url = item["Url"]
    ten = item["Ten van ban"]
    ngay_cap_nhat = item.get("Ngay cap nhat")
    
    print(f"[{stt}/{len(links)}] Crawling: {ten[:80]}...")
    
    try:
        data = extract_luoc_do_with_playwright(
            url=url,
            screenshots_dir=Path("data/screenshots"),
            cookies_path=Path("data/cookies.json"),
            headed=False,
            timeout_ms=60000,
            only_tab8=False,
            storage_state_path=Path("data/storage_state.json"),
            relogin_on_fail=True,
            download_tab8=False,
        )
        data["stt"] = stt
        if ngay_cap_nhat:
            data["Ngay cap nhat"] = ngay_cap_nhat
        results.append(data)
        
        total_rel = data.get("tab4_total_relations", 0)
        print(f"  ✓ Hoàn tất - Tổng {total_rel} quan hệ văn bản\n")
        
    except Exception as e:
        print(f"  ✗ Lỗi: {e}\n")
        results.append({"stt": stt, "url": url, "error": str(e)})

compact_results = compact_schema(results)
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(compact_results, f, ensure_ascii=False, indent=2)

# Lưu vào database
try:
    db = TVPLDatabase(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    print("\nĐang lưu vào database...")
    
    # Bắt đầu session
    session_id = db.start_crawl_session()
    print(f"✓ Bắt đầu session #{session_id}")
    
    # Lưu từng văn bản
    new_versions = 0
    unchanged = 0
    for item in compact_results:
        try:
            has_changed = db.save_document(item, session_id)
            if has_changed:
                new_versions += 1
            else:
                unchanged += 1
        except Exception as e:
            print(f"  Lỗi lưu doc_id {item.get('url', '')}: {e}")
    
    # Kết thúc session
    db.complete_crawl_session(session_id, len(compact_results), new_versions, unchanged)
    db.close()
    print(f"✓ Hoàn tất: {new_versions} thay đổi, {unchanged} không đổi")
except Exception as e:
    print(f"✗ Lỗi kết nối database: {e}")

print(f"\n{'='*60}")
print(f"Đã crawl xong {len(results)}/{len(links)} văn bản")
print(f"Kết quả lưu tại: {output_file}")
print(f"{'='*60}")

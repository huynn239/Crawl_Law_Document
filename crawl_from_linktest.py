# -*- coding: utf-8 -*-
"""Crawl dữ liệu từ LinkTest.json"""
import json
import sys
from pathlib import Path
from tvpl_crawler.playwright_extract_v2 import extract_luoc_do_with_playwright
from compact_schema import compact_schema

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Đọc LinkTest.json
links = json.loads(Path("data/LinkTest.json").read_text(encoding="utf-8"))

print(f"Bắt đầu crawl {len(links)} văn bản từ LinkTest.json...\n")

results = []
for item in links:
    stt = item["Stt"]
    url = item["Url"]
    ten = item["Tên văn bản"]
    
    print(f"[{stt}/{len(links)}] Crawling: {ten[:80]}...")
    
    try:
        data = extract_luoc_do_with_playwright(
            url=url,
            screenshots_dir=Path("data/screenshots"),
            cookies_path=Path("data/cookies.json"),
            headed=False,
            timeout_ms=30000,
            only_tab8=False,
            storage_state_path=Path("data/storage_state.json"),
            relogin_on_fail=True,
            download_tab8=False,
        )
        data["stt"] = stt
        results.append(data)
        
        # In tóm tắt
        total_rel = data.get("tab4_total_relations", 0)
        print(f"  ✓ Hoàn tất - Tổng {total_rel} quan hệ văn bản\n")
        
    except Exception as e:
        print(f"  ✗ Lỗi: {e}\n")
        results.append({"stt": stt, "url": url, "error": str(e)})

# Thu gọn schema và lưu kết quả
compact_results = compact_schema(results)
output_path = Path("data/LinkTest_Result.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(compact_results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Đã crawl xong {len(results)}/{len(links)} văn bản")
print(f"Kết quả lưu tại: {output_path}")
print(f"{'='*60}")

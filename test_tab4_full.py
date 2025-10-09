# -*- coding: utf-8 -*-
"""Test script để crawl đầy đủ Tab4 với hyperlink phân loại"""
import json
import sys
from pathlib import Path
from tvpl_crawler.playwright_extract import extract_luoc_do_with_playwright

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# URL test
url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"

# Crawl với headed mode để quan sát
result = extract_luoc_do_with_playwright(
    url=url,
    screenshots_dir=Path("data/screenshots"),
    cookies_path=Path("data/cookies.json"),
    headed=True,  # Bật để xem quá trình
    timeout_ms=30000,
    only_tab8=False,
    storage_state_path=Path("data/storage_state.json"),
    relogin_on_fail=True,
    download_tab8=False,
    downloads_dir=Path("data/downloads"),
)

# Lưu kết quả
output_path = Path("data/test_tab4_full_result.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump([result], f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Kết quả đã lưu vào: {output_path}")
print(f"{'='*60}\n")

# In tóm tắt
print("TÓM TẮT KẾT QUẢ:")
print(f"URL: {result.get('url')}")
print(f"\nThông tin cơ bản:")
for key in ["Số hiệu", "Loại văn bản", "Ngày ban hành", "Tình trạng"]:
    if key in result:
        print(f"  {key}: {result[key]}")

print(f"\nQuan hệ văn bản (Tab4):")
tab4_relations = result.get("tab4_relations", {})
tab4_summary = result.get("tab4_summary", {})
for rel_type, items in tab4_relations.items():
    count = len(items) if items else 0
    print(f"  {rel_type}: {count} văn bản")
    if items:
        for i, item in enumerate(items[:3], 1):  # Hiển thị 3 item đầu
            print(f"    {i}. {item.get('text', 'N/A')[:80]}")
        if count > 3:
            print(f"    ... và {count - 3} văn bản khác")

print(f"\nTổng số quan hệ: {result.get('tab4_total_relations', 0)}")

print(f"\nTab8 (Tải về):")
tab8_links = result.get("tab8_links", [])
print(f"  Số lượng link: {len(tab8_links)}")
for i, link in enumerate(tab8_links, 1):
    print(f"    {i}. {link.get('text', 'N/A')}")

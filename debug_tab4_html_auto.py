# -*- coding: utf-8 -*-
"""Debug script để xem cấu trúc HTML của Tab4 - tự động đóng"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(storage_state="data/storage_state.json")
    page = context.new_page()
    
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    
    # Click tab Lược đồ
    try:
        page.click("#aLuocDo")
    except:
        try:
            page.evaluate("() => { location.hash = '#tab4'; }")
        except:
            pass
    
    page.wait_for_timeout(2000)
    
    # Lấy HTML của tab4
    tab4_html = page.query_selector("#tab4")
    if tab4_html:
        html_content = tab4_html.inner_html()
        
        # Lưu HTML
        output_path = Path("data/tab4_debug.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"HTML của Tab4 đã lưu vào: {output_path}")
        
        # In text content
        text_content = tab4_html.inner_text()
        print("\n" + "="*60)
        print("TEXT CONTENT CỦA TAB4:")
        print("="*60)
        print(text_content[:2000])
        
        # Đếm số anchor
        anchors = page.query_selector_all("#tab4 a[href]")
        print(f"\n\nTổng số anchor trong Tab4: {len(anchors)}")
        
        # In 10 anchor đầu
        print("\n10 anchor đầu tiên:")
        for i, a in enumerate(anchors[:10], 1):
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip()[:80]
            print(f"  {i}. {text}")
            print(f"     -> {href}")
    else:
        print("Không tìm thấy #tab4")
    
    browser.close()

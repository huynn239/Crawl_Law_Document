# -*- coding: utf-8 -*-
"""
Fixed version - Thu thập hyperlink Tab4 theo cấu trúc HTML thực tế
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import json
import re

def extract_tab4_relations_fixed(url: str, storage_state_path: str = "data/storage_state.json"):
    """Thu thập hyperlink Tab4 với logic đúng cấu trúc HTML"""
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(storage_state=storage_state_path)
        page = context.new_page()
        
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Click tab Lược đồ
        try:
            page.click("#aLuocDo")
        except:
            page.evaluate("() => { location.hash = '#tab4'; }")
        
        page.wait_for_timeout(2000)
        
        # Click TẤT CẢ nút "Xem thêm" để hiện đầy đủ
        page.evaluate("""
            () => {
                // Tìm tất cả nút "Xem thêm" (class dgcvm)
                const buttons = document.querySelectorAll('.dgcvm');
                buttons.forEach(btn => {
                    try {
                        // Click để hiện thêm items
                        btn.click();
                    } catch(e) {}
                });
            }
        """)
        
        page.wait_for_timeout(1000)
        
        # Mapping nhãn tiếng Việt
        REL_LABELS = {
            "guidedDocument": "Văn bản được hướng dẫn",
            "DuocHopNhatDocument": "Văn bản hợp nhất",
            "amendedDocument": "Văn bản bị sửa đổi bổ sung",
            "correctedDocument": "Văn bản bị đính chính",
            "replacedDocument": "Văn bản bị thay thế",
            "referentialDocument": "Văn bản được dẫn chiếu",
            "basisDocument": "Văn bản được căn cứ",
            "contentConnection": "Văn bản liên quan cùng nội dung",
        }
        
        tab4_relations = {}
        
        # Thu thập từng nhóm theo ID
        for div_id, label in REL_LABELS.items():
            items = []
            try:
                # Tìm div chứa nhóm này
                div = page.query_selector(f"#{div_id}")
                if not div:
                    tab4_relations[label] = []
                    continue
                
                # Lấy tất cả anchor trong div này
                anchors = div.query_selector_all("a[href]")
                for a in anchors:
                    href = a.get_attribute("href") or ""
                    if not href or href.startswith('#'):
                        continue
                    
                    # Chỉ lấy link văn bản
                    if "/van-ban/" not in href.lower() and "/cong-van/" not in href.lower():
                        continue
                    
                    full_url = urljoin(page.url, href)
                    text = (a.inner_text() or "").strip()
                    text = re.sub(r"\s+", " ", text)
                    
                    # Bỏ qua link membership
                    if "regcustorder" in full_url.lower() or "action=chuyendoi" in full_url.lower():
                        continue
                    
                    item = {"text": text, "href": full_url}
                    if item not in items:
                        items.append(item)
                
                tab4_relations[label] = items
            except Exception as e:
                print(f"Error collecting {label}: {e}")
                tab4_relations[label] = []
        
        browser.close()
        
        return tab4_relations

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("Đang crawl Tab4...")
    relations = extract_tab4_relations_fixed(url)
    
    print("\n" + "="*60)
    print("KẾT QUẢ THU THẬP:")
    print("="*60)
    
    total = 0
    for label, items in relations.items():
        count = len(items)
        total += count
        print(f"\n{label}: {count} văn bản")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item['text'][:80]}")
            print(f"     -> {item['href']}")
    
    print(f"\nTổng số: {total} văn bản")
    
    # Lưu kết quả
    output = Path("data/tab4_fixed_result.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)
    
    print(f"\nĐã lưu vào: {output}")

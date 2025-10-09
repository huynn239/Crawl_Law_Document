# -*- coding: utf-8 -*-
"""Simplified Tab4 extraction logic"""
from urllib.parse import urljoin
import re

def extract_tab4_simple(page):
    """Thu thập đầy đủ thông tin Tab4: thông tin văn bản đang xem + 14 mục quan hệ văn bản"""
    
    # 1. Click tất cả nút "Xem thêm"
    try:
        page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('.dgcvm');
                buttons.forEach(btn => {
                    try { btn.click(); } catch(e) {}
                });
            }
        """)
        page.wait_for_timeout(1000)
    except Exception:
        pass
    
    # 2. Thu thập thông tin "Văn bản đang xem"
    doc_info = {}
    try:
        viewing_div = page.query_selector("#viewingDocument")
        if viewing_div:
            att_divs = viewing_div.query_selector_all(".att")
            for att in att_divs:
                try:
                    hd = att.query_selector(".hd")
                    ds = att.query_selector(".ds")
                    if hd and ds:
                        label = hd.inner_text().strip().rstrip(":")
                        value = ds.inner_text().strip()
                        if value and value != "...":
                            doc_info[label] = value
                except Exception:
                    continue
    except Exception:
        pass
    
    # 3. Thu thập 14 mục quan hệ văn bản theo ID
    REL_LABELS = {
        # Cột trái
        "guidedDocument": "Văn bản được hướng dẫn",
        "DuocHopNhatDocument": "Văn bản được hợp nhất",
        "amendedDocument": "Văn bản bị sửa đổi bổ sung",
        "correctedDocument": "Văn bản bị đính chính",
        "replacedDocument": "Văn bản bị thay thế",
        "referentialDocument": "Văn bản được dẫn chiếu",
        "basisDocument": "Văn bản được căn cứ",
        "languageConnection": "Văn bản liên quan ngôn ngữ",
        # Cột phải
        "guideDocument": "Văn bản hướng dẫn",
        "HopNhatDocument": "Văn bản hợp nhất",
        "amendDocument": "Văn bản sửa đổi bổ sung",
        "correctingDocument": "Văn bản đính chính",
        "replaceDocument": "Văn bản thay thế",
        "contentConnection": "Văn bản liên quan cùng nội dung",
    }
    
    tab4_relations = {}
    for div_id, label in REL_LABELS.items():
        items = []
        try:
            div = page.query_selector(f"#{div_id}")
            if div:
                anchors = div.query_selector_all("a[href]")
                for a in anchors:
                    href = a.get_attribute("href") or ""
                    if not href or href.startswith('#'):
                        continue
                    
                    # Chỉ lấy link văn bản
                    if "/van-ban/" not in href.lower() and "/cong-van/" not in href.lower():
                        continue
                    
                    # Bỏ qua link membership
                    if "regcustorder" in href.lower() or "action=chuyendoi" in href.lower():
                        continue
                    
                    full_url = urljoin(page.url, href)
                    text = (a.inner_text() or "").strip()
                    text = re.sub(r"\s+", " ", text)
                    
                    item = {"text": text, "href": full_url}
                    if item not in items:
                        items.append(item)
        except Exception:
            pass
        
        tab4_relations[label] = items
    
    # 4. Tóm tắt
    tab4_summary = {k: len(v) for k, v in tab4_relations.items()}
    tab4_total = sum(tab4_summary.values())
    
    return {
        "doc_info": doc_info,
        "tab4_relations": tab4_relations,
        "tab4_summary": tab4_summary,
        "tab4_total_relations": tab4_total
    }

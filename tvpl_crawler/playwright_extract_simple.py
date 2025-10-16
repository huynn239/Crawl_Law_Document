# -*- coding: utf-8 -*-
"""Simple extract logic for tab4 (Lược đồ) - async version"""
import re
from urllib.parse import urljoin


async def extract_tab4_simple_async(page):
    """Extract tab4 relations and doc_info from page (async)"""
    
    # 1. Extract doc_info from 'Văn bản đang xem' in tab4
    doc_info = {}
    try:
        viewing_doc = await page.query_selector("#viewingDocument")
        if viewing_doc:
            att_divs = await viewing_doc.query_selector_all(".att")
            for att_div in att_divs:
                hd = await att_div.query_selector(".hd")
                ds = await att_div.query_selector(".ds")
                if hd and ds:
                    label = (await hd.inner_text()).strip().rstrip(":")
                    value = (await ds.inner_text()).strip()
                    if value and value not in ["", "..."]:
                        doc_info[label] = value
    except Exception as e:
        pass
    
    # 2. Extract tab4 relations - LOGIC ĐƠN GIẢN
    tab4_relations = {}
    tab4_summary = {}
    tab4_total = 0
    
    try:
        # Lấy toàn bộ HTML của tab4
        tab4_html = await page.locator("#tab4").inner_html()
        
        # Strategy: Find <div class="ghd">TITLE - [N]</div> then find next <div...class="ct"...>CONTENT</div>
        # Split by looking for pattern pairs
        
        # Find all ghd divs with their positions
        ghd_pattern = r'<div\s+class="ghd[^"]*"[^>]*>'
        ghd_starts = [m.start() for m in re.finditer(ghd_pattern, tab4_html)]
        
        for ghd_start in ghd_starts:
            # Find the closing </div> for this ghd
            ghd_close = tab4_html.find('</div>', ghd_start)
            if ghd_close == -1:
                continue
            
            ghd_content = tab4_html[ghd_start:ghd_close]
            
            # Extract title and count from ghd
            title_match = re.search(r'>([^<]*(?:<font[^>]*>[^<]*</font>)?[^<]*)\s*-\s*\[<b>(\d+)</b>\]', ghd_content)
            if not title_match:
                continue
            
            title_raw = title_match.group(1)
            count = int(title_match.group(2))
            
            # Clean title
            title_text = re.sub(r'<[^>]+>', '', title_raw).strip()
            if not title_text:
                continue
            
            # Find the next <div...class="ct"...> after this ghd
            ct_start = tab4_html.find('class="ct"', ghd_close)
            if ct_start == -1:
                tab4_relations[title_text] = []
                tab4_summary[title_text] = 0
                continue
            
            # Find the opening < of that div
            ct_div_start = tab4_html.rfind('<div', ghd_close, ct_start + 20)
            if ct_div_start == -1:
                tab4_relations[title_text] = []
                tab4_summary[title_text] = 0
                continue
            
            # Find closing </div> for ct section (find next cmVsep or next ghd)
            next_ghd = tab4_html.find('<div class="ghd', ct_div_start + 1)
            next_sep = tab4_html.find('class="cmVsep"', ct_div_start + 1)
            
            if next_ghd == -1 and next_sep == -1:
                ct_end = len(tab4_html)
            elif next_ghd == -1:
                ct_end = next_sep
            elif next_sep == -1:
                ct_end = next_ghd
            else:
                ct_end = min(next_ghd, next_sep)
            
            content_section = tab4_html[ct_div_start:ct_end]
            
            # Extract all links with van-ban in href
            link_pattern = r'<a[^>]+href="([^"]*van-ban[^"]*?)"[^>]*>([^<]+)</a>'
            links = re.findall(link_pattern, content_section)
            
            relations_list = []
            for href, text in links:
                text = text.strip()
                href = href.strip()
                if href and text and len(text) > 10:  # Filter out short noise
                    if href.startswith("/"):
                        href = f"https://thuvienphapluat.vn{href}"
                    relations_list.append({"text": text, "href": href})
            
            tab4_relations[title_text] = relations_list
            tab4_summary[title_text] = len(relations_list)
            tab4_total += len(relations_list)
    except Exception as e:
        import traceback
        print(f"Error extracting tab4: {e}")
        traceback.print_exc()
    
    return {
        "doc_info": doc_info,
        "tab4_relations": tab4_relations,
        "tab4_summary": tab4_summary,
        "tab4_total_relations": tab4_total
    }

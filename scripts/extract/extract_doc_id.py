#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract doc_id from URL"""
import re

def extract_doc_id(url: str) -> str:
    """
    Extract doc_id from thuvienphapluat.vn URL
    
    Examples:
        https://.../-677890.aspx → 677890
        https://.../-123456.aspx?dll=true → 123456
    """
    # Pattern: số cuối cùng trước .aspx
    match = re.search(r'-(\d+)\.aspx', url)
    if match:
        return match.group(1)
    return None

# Test
if __name__ == "__main__":
    test_urls = [
        "https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Quyet-dinh-3563-QD-BTC-2025-cong-bo-thu-tuc-hanh-chinh-linh-vuc-quan-ly-thue-677890.aspx",
        "https://thuvienphapluat.vn/van-ban/Bo-may-hanh-chinh/Chi-thi-32-CT-TTg-2025-cong-tac-bao-ve-bi-mat-Nha-nuoc-trong-tinh-hinh-moi-677946.aspx?dll=true",
    ]
    
    for url in test_urls:
        doc_id = extract_doc_id(url)
        print(f"URL: {url}")
        print(f"doc_id: {doc_id}\n")

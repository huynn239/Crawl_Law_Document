#!/usr/bin/env python3
"""
Simple tab1 crawler using existing tools
"""

import asyncio
import json
import os

async def main():
    """Use existing crawler tools to get tab1 content"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("Using crawl_data_fast.py to get content...")
    
    # Create a simple links file
    links_data = [{"Stt": 1, "Tên văn bản": "Thông tư 21/2025", "Url": url}]
    
    os.makedirs('data', exist_ok=True)
    with open('data/single_link.json', 'w', encoding='utf-8') as f:
        json.dump(links_data, f, ensure_ascii=False, indent=2)
    
    print("Created single link file: data/single_link.json")
    print("Now run: python crawl_data_fast.py data/single_link.json")
    print("This will extract tab1 content with formulas")

if __name__ == "__main__":
    asyncio.run(main())
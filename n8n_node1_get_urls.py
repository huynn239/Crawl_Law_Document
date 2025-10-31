#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N8N Node 1: Crawl hyperlinks và insert vào Supabase"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def crawl_hyperlinks(
    search_url: str,
    max_pages: int = 5,
    cookies_file: str = "data/cookies.json"
) -> list:
    """Crawl hyperlinks từ trang tìm kiếm"""
    
    # Tạo file output tạm
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(f"data/temp_links_{timestamp}.json")
    
    # Command crawl hyperlinks
    cmd = [
        sys.executable, "-m", "tvpl_crawler", "links-basic",
        "-u", search_url,
        "-o", str(output_file),
        "-m", str(max_pages),
        "--page-param", "page",
        "--cookies", cookies_file
    ]
    
    print(f"🔍 Crawling hyperlinks from: {search_url}")
    print(f"   Max pages: {max_pages}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return []
    
    # Đọc kết quả
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            links = json.load(f)
        
        print(f"✅ Found {len(links)} URLs")
        
        # Cleanup temp file
        output_file.unlink()
        
        return links
    
    return []

def extract_doc_id(url: str) -> str:
    """Extract doc_id from URL"""
    import re
    match = re.search(r'-(\d+)\.aspx', url)
    return match.group(1) if match else None

def transform_for_supabase(links: list) -> list:
    """Transform sang format Supabase doc_urls"""
    return [
        {
            "url": item["Url"],
            "doc_id": extract_doc_id(item["Url"]),
            "status": "pending",
            "crawl_priority": 0,
            "retry_count": 0
        }
        for item in links
    ]

def main():
    """Main function for n8n"""
    if len(sys.argv) < 2:
        print("Usage: python n8n_node1_get_urls.py <search_url> [max_pages]")
        print("Example: python n8n_node1_get_urls.py 'https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0' 5")
        sys.exit(1)
    
    search_url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    # Crawl hyperlinks
    links = crawl_hyperlinks(search_url, max_pages)
    
    if not links:
        print("❌ No links found")
        sys.exit(1)
    
    # Transform for Supabase
    supabase_data = transform_for_supabase(links)
    
    # Output JSON cho n8n
    print("\n📤 OUTPUT FOR N8N:")
    print(json.dumps(supabase_data, ensure_ascii=False, indent=2))
    
    # Save to file for n8n to read
    output_file = Path("data/n8n_urls_output.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(supabase_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")

if __name__ == "__main__":
    main()

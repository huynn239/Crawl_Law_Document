#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N8N Node 2: Crawl document data và transform cho Supabase"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import hashlib

def crawl_documents(urls: list, concurrency: int = 2) -> list:
    """Crawl document data từ list URLs"""
    
    # Tạo file input
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file = Path(f"data/temp_input_{timestamp}.json")
    output_file = Path(f"data/temp_output_{timestamp}.json")
    
    # Format input cho crawl_data_fast
    links = [
        {"Stt": i+1, "Url": url, "Ten van ban": ""}
        for i, url in enumerate(urls)
    ]
    
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    
    # Command crawl documents
    cmd = [
        sys.executable, "crawl_data_fast.py",
        str(input_file),
        str(output_file),
        str(concurrency),
        "30000",
        "--reuse-session"
    ]
    
    print(f"🚀 Crawling {len(urls)} documents...")
    print(f"   Concurrency: {concurrency}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Đọc kết quả
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Crawled {len(data)} documents")
        
        # Cleanup
        input_file.unlink()
        output_file.unlink()
        
        return data
    
    print(f"❌ Error: {result.stderr}")
    return []

def parse_date(date_str: str):
    """Parse Vietnamese date to ISO format"""
    if not date_str or date_str == "Dữ liệu đang cập nhật":
        return None
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return None

def generate_hash(doc_info: dict) -> str:
    """Generate content hash"""
    content = json.dumps(doc_info, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode()).hexdigest()

def transform_for_supabase(crawled_data: list) -> dict:
    """Transform sang format Supabase - Optimized"""
    
    result = {
        "doc_metadata": [],
        "relationships": [],
        "doc_files": []
    }
    
    for item in crawled_data:
        url = item.get("url")
        doc_info = item.get("doc_info", {})
        
        if not doc_info or not url:
            continue
        
        # 1. doc_metadata - Chỉ lưu fields cần thiết
        metadata = {
            "url": url,
            "so_hieu": doc_info.get("Số hiệu"),
            "loai_van_ban": doc_info.get("Loại văn bản"),
            "linh_vuc": doc_info.get("Lĩnh vực, ngành"),
            "noi_ban_hanh": doc_info.get("Nơi ban hành"),
            "nguoi_ky": doc_info.get("Người ký"),
            "ngay_ban_hanh": parse_date(doc_info.get("Ngày ban hành")),
            "ngay_hieu_luc": parse_date(doc_info.get("Ngày hiệu lực")),
            "ngay_cap_nhat": parse_date(item.get("ngay_cap_nhat")),  # Từ links.json
            "tinh_trang": doc_info.get("Tình trạng"),
            "content_hash": generate_hash(doc_info)
        }
        result["doc_metadata"].append(metadata)
        
        # 2. relationships - Chỉ lưu quan hệ có data
        tab4 = item.get("tab4", {})
        relations = tab4.get("relations", {})
        
        for rel_type, rel_list in relations.items():
            if not rel_list or len(rel_list) == 0:
                continue
            
            rel_type_normalized = rel_type.lower().replace(" ", "_")
            
            for rel in rel_list:
                href = rel.get("href")
                if not href:  # Skip nếu không có href
                    continue
                    
                relationship = {
                    "source_url": url,
                    "target_doc_url": href,
                    "target_text": rel.get("text"),
                    "relationship_type": rel_type_normalized
                }
                result["relationships"].append(relationship)
        
        # 3. doc_files
        tab8 = item.get("tab8", {})
        links = tab8.get("links", [])
        
        for link in links:
            file_text = link.get("text", "").lower()
            
            if "pdf" in file_text:
                file_type = "pdf"
            elif "docx" in file_text:
                file_type = "docx"
            elif "doc" in file_text:
                file_type = "doc"
            else:
                file_type = "other"
            
            doc_file = {
                "source_url": url,
                "file_type": file_type,
                "file_url": link.get("href"),
                "file_name": link.get("text")
            }
            result["doc_files"].append(doc_file)
    
    return result

def main():
    """Main function for n8n"""
    if len(sys.argv) < 2:
        print("Usage: python n8n_node2_crawl_docs.py <urls_json_file> [concurrency]")
        print("Example: python n8n_node2_crawl_docs.py data/urls.json 2")
        sys.exit(1)
    
    urls_file = Path(sys.argv[1])
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    # Đọc URLs
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls_data = json.load(f)
    
    # Extract URLs
    if isinstance(urls_data, list):
        if isinstance(urls_data[0], dict) and "url" in urls_data[0]:
            urls = [item["url"] for item in urls_data]
        else:
            urls = urls_data
    else:
        print("❌ Invalid input format")
        sys.exit(1)
    
    # Crawl documents
    crawled_data = crawl_documents(urls, concurrency)
    
    if not crawled_data:
        print("❌ No data crawled")
        sys.exit(1)
    
    # Transform for Supabase
    supabase_data = transform_for_supabase(crawled_data)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Metadata: {len(supabase_data['doc_metadata'])}")
    print(f"   Relationships: {len(supabase_data['relationships'])}")
    print(f"   Files: {len(supabase_data['doc_files'])}")
    
    # Save output for n8n
    output_file = Path("data/n8n_supabase_output.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(supabase_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")
    
    # Also print to stdout for n8n
    print("\n📤 OUTPUT FOR N8N:")
    print(json.dumps(supabase_data, ensure_ascii=False))

if __name__ == "__main__":
    main()

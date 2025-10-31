#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transform crawled data to Supabase format - Dùng với crawl_data_fast.py"""
import json
import sys
import hashlib
import re
from pathlib import Path

def extract_doc_id(url: str) -> str:
    """Extract doc_id from URL"""
    match = re.search(r'-(\d+)\.aspx', url)
    return match.group(1) if match else None

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

def transform_to_supabase(crawled_data: list) -> dict:
    """Transform output từ crawl_data_fast.py sang Supabase format"""
    
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
        
        # 1. doc_metadata (+ raw_data JSONB)
        doc_id = extract_doc_id(url)
        # Parse tình trạng thành boolean
        tinh_trang_str = doc_info.get("Tình trạng", "")
        con_hieu_luc = "Còn hiệu lực" in tinh_trang_str if tinh_trang_str else None
        
        metadata = {
            "url": url,
            "doc_id": doc_id,
            "con_hieu_luc": con_hieu_luc,
            "content_hash": generate_hash(doc_info),
            "extra_data": doc_info  # Lưu toàn bộ doc_info vào JSONB
        }
        result["doc_metadata"].append(metadata)
        
        # 2. relationships
        tab4 = item.get("tab4", {})
        relations = tab4.get("relations", {})
        
        for rel_type, rel_list in relations.items():
            if not rel_list or len(rel_list) == 0:
                continue
            
            rel_type_normalized = rel_type.lower().replace(" ", "_")
            
            for rel in rel_list:
                href = rel.get("href")
                if not href:
                    continue
                
                # Extract target_doc_id from URL
                target_doc_id = extract_doc_id(href)
                    
                relationship = {
                    "source_url": url,
                    "source_doc_id": doc_id,
                    "target_doc_url": href,
                    "target_doc_id": target_doc_id,
                    "relationship_type": rel_type_normalized
                }
                result["relationships"].append(relationship)
        
        # 3. doc_files - CHỈ LẤY 1 FILE (ƯU TIÊN PDF)
        tab8 = item.get("tab8", {})
        links = tab8.get("links", [])
        
        pdf_link = next((link for link in links if "pdf" in link.get("text", "").lower()), None)
        selected_link = pdf_link or (links[0] if links else None)
        
        if selected_link:
            file_text = selected_link.get("text", "").lower()
            
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
                "source_doc_id": doc_id,  # Thêm source_doc_id
                "file_url": selected_link.get("href"),
                "file_name": selected_link.get("text"),
                "file_type": file_type
            }
            result["doc_files"].append(doc_file)
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python supabase_transform.py <input_json> [output_json]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    supabase_data = transform_to_supabase(data)
    
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(str(input_file).replace('.json', '_supabase.json'))
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(supabase_data, f, ensure_ascii=False, indent=2)
    
    print(f"Transformed {len(data)} docs -> {output_file}")

if __name__ == "__main__":
    main()

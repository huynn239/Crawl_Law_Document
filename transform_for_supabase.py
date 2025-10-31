#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transform crawled data to Supabase format"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List

def parse_date(date_str: str):
    """Parse Vietnamese date format to ISO"""
    if not date_str or date_str == "Dữ liệu đang cập nhật":
        return None
    try:
        # Format: 21/10/2025
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return None

def generate_content_hash(doc_info: Dict) -> str:
    """Generate MD5 hash of doc_info for change detection"""
    content = json.dumps(doc_info, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode()).hexdigest()

def transform_to_supabase(crawled_data: List[Dict]) -> Dict:
    """Transform crawled data to Supabase insert format"""
    
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
        
        # 1. doc_metadata
        metadata = {
            "url": url,  # n8n sẽ lookup doc_url_id
            "so_hieu": doc_info.get("Số hiệu"),
            "loai_van_ban": doc_info.get("Loại văn bản"),
            "linh_vuc": doc_info.get("Lĩnh vực, ngành"),
            "noi_ban_hanh": doc_info.get("Nơi ban hành"),
            "nguoi_ky": doc_info.get("Người ký"),
            "ngay_ban_hanh": parse_date(doc_info.get("Ngày ban hành")),
            "ngay_hieu_luc": parse_date(doc_info.get("Ngày hiệu lực")),
            "ngay_dang": parse_date(doc_info.get("Ngày đăng")),
            "so_cong_bao": doc_info.get("Số công báo"),
            "tinh_trang": doc_info.get("Tình trạng"),
            "raw_json": item,  # Lưu toàn bộ
            "content_hash": generate_content_hash(doc_info)
        }
        result["doc_metadata"].append(metadata)
        
        # 2. relationships
        tab4 = item.get("tab4", {})
        relations = tab4.get("relations", {})
        
        for rel_type, rel_list in relations.items():
            if not rel_list:
                continue
            
            # Normalize relationship type
            rel_type_normalized = rel_type.lower().replace(" ", "_")
            
            for rel in rel_list:
                relationship = {
                    "source_url": url,  # n8n sẽ lookup source_doc_id
                    "target_doc_url": rel.get("href"),
                    "target_text": rel.get("text"),
                    "relationship_type": rel_type_normalized
                }
                result["relationships"].append(relationship)
        
        # 3. doc_files
        tab8 = item.get("tab8", {})
        links = tab8.get("links", [])
        
        for link in links:
            file_text = link.get("text", "").lower()
            
            # Detect file type
            if "pdf" in file_text:
                file_type = "pdf"
            elif "doc" in file_text and "docx" not in file_text:
                file_type = "doc"
            elif "docx" in file_text:
                file_type = "docx"
            else:
                file_type = "other"
            
            doc_file = {
                "source_url": url,  # n8n sẽ lookup doc_metadata_id
                "file_type": file_type,
                "file_url": link.get("href"),
                "file_name": link.get("text")
            }
            result["doc_files"].append(doc_file)
    
    return result

def main():
    """Test transformation"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python transform_for_supabase.py <input_json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    transformed = transform_to_supabase(data)
    
    print(f"Transformed {len(data)} documents:")
    print(f"  - Metadata: {len(transformed['doc_metadata'])}")
    print(f"  - Relationships: {len(transformed['relationships'])}")
    print(f"  - Files: {len(transformed['doc_files'])}")
    
    # Save output
    output_file = input_file.replace('.json', '_supabase.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to: {output_file}")

if __name__ == "__main__":
    main()

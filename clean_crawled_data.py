#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clean crawled data - Remove unnecessary fields"""
import json
import sys
from pathlib import Path

def clean_item(item: dict) -> dict:
    """Remove unnecessary fields from crawled item"""
    
    # Chỉ giữ fields cần thiết
    cleaned = {
        "url": item.get("url"),
        "doc_info": item.get("doc_info", {}),
        "tab4": {
            "relations": item.get("tab4", {}).get("relations", {})
        },
        "tab8": {
            "links": item.get("tab8", {}).get("links", [])
        }
    }
    
    # Lọc bỏ relations rỗng
    relations = cleaned["tab4"]["relations"]
    cleaned["tab4"]["relations"] = {
        k: v for k, v in relations.items() 
        if v and len(v) > 0
    }
    
    return cleaned

def clean_file(input_file: str, output_file: str = None):
    """Clean entire JSON file"""
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ File not found: {input_file}")
        return
    
    # Read data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Clean each item
    cleaned_data = [clean_item(item) for item in data]
    
    # Output file
    if not output_file:
        output_file = str(input_path).replace('.json', '_cleaned.json')
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    # Stats
    original_size = input_path.stat().st_size
    cleaned_size = Path(output_file).stat().st_size
    reduction = (1 - cleaned_size / original_size) * 100
    
    print(f"✅ Cleaned data saved to: {output_file}")
    print(f"📊 Size reduction: {reduction:.1f}%")
    print(f"   Original: {original_size:,} bytes")
    print(f"   Cleaned: {cleaned_size:,} bytes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clean_crawled_data.py <input_file> [output_file]")
        print("Example: python clean_crawled_data.py data/result.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    clean_file(input_file, output_file)

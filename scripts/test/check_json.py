import json
import sys

if len(sys.argv) < 2:
    print("Usage: python check_json.py <json_file>")
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
    
print(f"Total records: {len(data)}")
print(f"\nFirst record keys: {list(data[0].keys())}")
print(f"\nngay_cap_nhat: {data[0].get('ngay_cap_nhat')}")
print(f"\nSample doc_info: {data[0].get('doc_info', {})}")

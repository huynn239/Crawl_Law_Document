# -*- coding: utf-8 -*-
"""Kiểm tra chi tiết duplicate term_name"""
import os
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Kiểm tra chi tiết duplicate term_name...\n")

# Lấy tất cả terms
result = supabase.table('terms').select('term_id, term_name, url, definition').execute()
terms = result.data

# Tìm duplicate names
name_groups = {}
for term in terms:
    name = term['term_name']
    if name not in name_groups:
        name_groups[name] = []
    name_groups[name].append(term)

# Lọc chỉ lấy duplicates
duplicates = {name: terms for name, terms in name_groups.items() if len(terms) > 1}

print(f"⚠️  Tìm thấy {len(duplicates)} term_name bị duplicate\n")

for name, terms in duplicates.items():
    print(f"📌 {name} ({len(terms)} lần):")
    for term in terms:
        print(f"  → ID {term['term_id']}")
        print(f"     URL: {term['url']}")
        print(f"     Định nghĩa: {term['definition'][:100]}...")
        print()

print("="*60)
print("💡 KẾT LUẬN:")
print("="*60)
print("""
Nếu các terms có:
- ✅ CÙNG TÊN nhưng KHÁC URL → ĐÚNG (không phải duplicate)
- ⚠️ CÙNG TÊN và CÙNG URL → SAI (duplicate thật)

Ví dụ:
- "Sở Công Thương" ở Hà Nội vs "Sở Công Thương" ở TP.HCM → OK
- "Sở Công Thương" cùng URL → Duplicate
""")

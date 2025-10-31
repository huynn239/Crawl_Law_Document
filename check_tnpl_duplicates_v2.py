# -*- coding: utf-8 -*-
"""Kiểm tra duplicate terms trong Supabase (phiên bản chính xác)"""
import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Kiểm tra duplicate terms trong Supabase...\n")

# 1. Tổng số terms
result = supabase.from_('tnpl.terms').select('term_id', count='exact').execute()
total_terms = result.count
print(f"📊 Tổng số terms: {total_terms}")

# 2. Lấy tất cả terms (pagination)
print("\n⏳ Đang lấy dữ liệu...")
all_terms = []
page_size = 1000
offset = 0

while True:
    result = supabase.from_('tnpl.terms').select('term_id, term_name, url, created_at').range(offset, offset + page_size - 1).execute()
    if not result.data:
        break
    all_terms.extend(result.data)
    offset += page_size
    print(f"  ⏳ Đã lấy {len(all_terms)} terms...")

print(f"  ✓ Đã lấy {len(all_terms)} terms\n")

# 3. Tìm duplicate URLs
print("🔎 Kiểm tra duplicate URLs...")
url_map = defaultdict(list)
for term in all_terms:
    url_map[term['url']].append(term)

duplicates = {url: terms for url, terms in url_map.items() if len(terms) > 1}

if duplicates:
    print(f"⚠️  Tìm thấy {len(duplicates)} URLs bị duplicate:\n")
    for url, terms in list(duplicates.items())[:10]:
        print(f"  📌 {url}: {len(terms)} lần")
        for term in terms:
            print(f"    → ID {term['term_id']}: {term['term_name'][:50]}... ({term['created_at']})")
        print()
    
    if len(duplicates) > 10:
        print(f"  ... và {len(duplicates) - 10} URLs khác\n")
    
    total_duplicates = sum(len(terms) - 1 for terms in duplicates.values())
    print(f"💡 Tổng số records duplicate: {total_duplicates}")
    print(f"💡 Số terms unique thực tế: {total_terms - total_duplicates} (nên là 14697)")
else:
    print("✓ Không có duplicate URLs")

print("\n" + "="*60)
print("💡 FIX DUPLICATE:")
print("="*60)
print("python fix_tnpl_duplicates.py")

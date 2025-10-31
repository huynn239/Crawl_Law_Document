# -*- coding: utf-8 -*-
"""Kiểm tra duplicate terms trong Supabase"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Kiểm tra duplicate terms trong Supabase...\n")

# 1. Tổng số terms
result = supabase.table('terms').select('term_id', count='exact').execute()
total_terms = result.count
print(f"📊 Tổng số terms: {total_terms}")

# 2. Kiểm tra duplicate URLs
print("\n🔎 Kiểm tra duplicate URLs...")
try:
    # Lấy tất cả URLs
    result = supabase.table('terms').select('url').execute()
    urls = [row['url'] for row in result.data]
    
    # Tìm duplicate
    from collections import Counter
    url_counts = Counter(urls)
    duplicates = {url: count for url, count in url_counts.items() if count > 1}
    
    if duplicates:
        print(f"⚠️  Tìm thấy {len(duplicates)} URLs bị duplicate:")
        for url, count in list(duplicates.items())[:10]:
            print(f"  - {url}: {count} lần")
            # Lấy chi tiết
            result = supabase.table('terms').select('term_id, term_name, created_at').eq('url', url).execute()
            for term in result.data:
                print(f"    → ID {term['term_id']}: {term['term_name'][:50]}... ({term['created_at']})")
        
        if len(duplicates) > 10:
            print(f"  ... và {len(duplicates) - 10} URLs khác")
        
        # Tính tổng số duplicate records
        total_duplicates = sum(count - 1 for count in duplicates.values())
        print(f"\n💡 Tổng số records duplicate: {total_duplicates}")
        print(f"💡 Số terms unique thực tế: {total_terms - total_duplicates}")
    else:
        print("✓ Không có duplicate URLs")
except Exception as e:
    print(f"✗ Lỗi: {e}")

# 3. Kiểm tra duplicate term_name
print("\n🔎 Kiểm tra duplicate term_name...")
try:
    result = supabase.table('terms').select('term_name').execute()
    names = [row['term_name'] for row in result.data]
    
    name_counts = Counter(names)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    
    if duplicates:
        print(f"⚠️  Tìm thấy {len(duplicates)} term_name bị duplicate:")
        for name, count in list(duplicates.items())[:10]:
            print(f"  - {name}: {count} lần")
        
        if len(duplicates) > 10:
            print(f"  ... và {len(duplicates) - 10} names khác")
    else:
        print("✓ Không có duplicate term_name")
except Exception as e:
    print(f"✗ Lỗi: {e}")

# 4. Gợi ý fix
print("\n" + "="*60)
print("💡 CÁCH FIX DUPLICATE:")
print("="*60)
print("""
1. Xóa duplicate URLs (giữ lại record cũ nhất):
   python fix_tnpl_duplicates.py

2. Hoặc xóa thủ công trong Supabase SQL Editor:
   DELETE FROM tnpl_terms a
   USING tnpl_terms b
   WHERE a.term_id > b.term_id
   AND a.url = b.url;
""")

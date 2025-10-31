# -*- coding: utf-8 -*-
"""Xóa duplicate terms trong Supabase (giữ lại record cũ nhất)"""
import os
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔧 Xóa duplicate terms trong Supabase...\n")

# 1. Tìm duplicate URLs
print("🔎 Tìm duplicate URLs...")
result = supabase.from_('tnpl.terms').select('term_id, url, created_at').order('url').execute()
terms = result.data

# Group by URL
from collections import defaultdict
url_groups = defaultdict(list)
for term in terms:
    url_groups[term['url']].append(term)

# Tìm duplicates
duplicates = {url: terms for url, terms in url_groups.items() if len(terms) > 1}

if not duplicates:
    print("✓ Không có duplicate URLs")
    exit(0)

print(f"⚠️  Tìm thấy {len(duplicates)} URLs bị duplicate")

# 2. Xác nhận
total_to_delete = sum(len(terms) - 1 for terms in duplicates.values())
print(f"💡 Sẽ xóa {total_to_delete} records duplicate (giữ lại record cũ nhất)")
print("\nVí dụ:")
for url, terms in list(duplicates.items())[:3]:
    print(f"\n  URL: {url}")
    for i, term in enumerate(terms):
        status = "KEEP" if i == 0 else "DELETE"
        print(f"    [{status}] ID {term['term_id']} - {term['created_at']}")

confirm = input(f"\n⚠️  Xác nhận xóa {total_to_delete} records? (yes/no): ")
if confirm.lower() != 'yes':
    print("❌ Hủy bỏ")
    exit(0)

# 3. Xóa duplicates
print("\n🗑️  Đang xóa duplicates...")
deleted_count = 0

for url, terms in duplicates.items():
    # Sắp xếp theo created_at (giữ lại cái cũ nhất)
    terms_sorted = sorted(terms, key=lambda x: x['created_at'])
    
    # Xóa các records sau (giữ lại cái đầu tiên)
    for term in terms_sorted[1:]:
        try:
            supabase.from_('tnpl.terms').delete().eq('term_id', term['term_id']).execute()
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"  Đã xóa {deleted_count}/{total_to_delete}...")
        except Exception as e:
            print(f"  ✗ Lỗi xóa ID {term['term_id']}: {e}")

print(f"\n✅ Hoàn tất! Đã xóa {deleted_count} duplicate records")

# 4. Kiểm tra lại
result = supabase.from_('tnpl.terms').select('term_id', count='exact').execute()
print(f"📊 Tổng số terms sau khi xóa: {result.count}")

"""Check if DB has data"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

print(f"Connecting to: {url}")

supabase = create_client(url, key)

# Check doc_urls count
result = supabase.table('crawl_url').select('*', count='exact').limit(5).execute()
print(f"\ndoc_urls count: {result.count}")
if result.data:
    print("Sample URLs:")
    for row in result.data[:3]:
        print(f"  - {row.get('url')} (status: {row.get('status')})")

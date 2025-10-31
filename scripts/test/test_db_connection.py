"""Test Supabase connection"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

print(f"Testing connection to: {url}")

try:
    supabase = create_client(url, key)
    result = supabase.table('crawl_url').select('count', count='exact').limit(1).execute()
    print(f"[OK] Connected! Total doc_urls: {result.count}")
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")

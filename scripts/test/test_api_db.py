"""Test API and check which DB it's using"""
import requests
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Test API
print("Testing API...")
response = requests.post("http://localhost:8000/links-basic", json={
    "url": "https://thuvienphapluat.vn/page/tim-van-ban.aspx",
    "max_pages": 1,
    "only_basic": True
})

if response.status_code == 200:
    data = response.json()
    print(f"API returned {len(data)} links")
    
    # Check DB
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    print(f"\nChecking DB at: {url}")
    
    supabase = create_client(url, key)
    result = supabase.table('crawl_url').select('*', count='exact').limit(3).execute()
    
    print(f"DB has {result.count} URLs")
    if result.data:
        print("Sample:")
        for row in result.data[:2]:
            print(f"  - {row.get('url')}")
else:
    print(f"API error: {response.status_code}")

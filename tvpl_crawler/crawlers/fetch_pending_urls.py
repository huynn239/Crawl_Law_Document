"""Fetch pending URLs from doc_urls table"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def fetch_pending_urls(limit=None, output_file=None):
    """Fetch URLs with status='pending' from doc_urls table"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise Exception("Missing SUPABASE_URL or SUPABASE_KEY")
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Query pending and failed URLs (retry failed with limit)
    # Priority: pending (priority desc) > failed (retry_count asc, max 3 retries)
    links = []
    page_size = 1000
    offset = 0
    
    while True:
        # Get pending first
        query = supabase.table('crawl_url').select('url, title, last_update_date, retry_count').eq('status', 'pending').order('priority', desc=True).range(offset, offset + page_size - 1)
        
        response = query.execute()
        
        if not response.data:
            break
        
        for row in response.data:
            links.append(row)
        
        offset += page_size
        
        # Stop if we have enough or no more data
        if limit and len(links) >= limit:
            links = links[:limit]
            break
        
        if len(response.data) < page_size:
            break
    
    # Format with Stt
    formatted_links = []
    for idx, row in enumerate(links, start=1):
        formatted_links.append({
            "Stt": idx,
            "Ten van ban": row['title'],
            "Url": row['url'],
            "Ngay cap nhat": row.get('last_update_date', '')
        })
    
    print(f"Fetched {len(formatted_links)} pending URLs")
    
    # Save to file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_links, f, ensure_ascii=False, indent=2)
        print(f"Saved to {output_file}")
    
    return formatted_links

if __name__ == '__main__':
    import sys
    
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    output = sys.argv[2] if len(sys.argv) > 2 else 'data/pending_urls.json'
    
    fetch_pending_urls(limit, output)

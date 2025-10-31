"""Upsert crawled links to doc_urls table with smart update logic"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def parse_date(date_str: str):
    """Parse DD/MM/YYYY to YYYY-MM-DD"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return None

def upsert_links(links: list) -> dict:
    """
    Upsert links to doc_urls table with smart logic:
    - If URL exists and status='completed': check if ngay_cap_nhat changed → update if changed
    - If URL exists and status='pending': always update
    - If URL not exists: insert new
    
    Returns: {inserted: int, updated: int, skipped: int}
    """
    inserted = 0
    updated = 0
    skipped = 0
    
    for item in links:
        url_str = item.get("Url") or item.get("url")
        if not url_str:
            continue
        
        doc_id = url_str.split("-")[-1].replace(".aspx", "") if url_str else None
        title = item.get("Ten van ban") or item.get("ten_van_ban") or ""
        ngay_cap_nhat = item.get("Ngay cap nhat") or item.get("ngay_cap_nhat") or ""
        ngay_cap_nhat_parsed = parse_date(ngay_cap_nhat)
        
        # Check if URL exists
        existing = supabase.from_('system.crawl_url').select('status, last_update_date').eq('url', url_str).execute()
        
        if existing.data:
            # URL exists
            old_status = existing.data[0].get('status')
            old_update_date = existing.data[0].get('last_update_date')
            
            # Case 1: Already completed - check if ngay_cap_nhat changed
            if old_status == 'completed':
                if ngay_cap_nhat_parsed and old_update_date and ngay_cap_nhat_parsed > old_update_date:
                    # Update: ngay_cap_nhat changed
                    supabase.from_('system.crawl_url').update({
                        'title': title,
                        'last_update_date': ngay_cap_nhat_parsed,
                        'status': 'pending',  # Reset to pending for re-crawl
                        'priority': 1  # Higher priority for changed docs
                    }).eq('url', url_str).execute()
                    updated += 1
                else:
                    # Skip: no change
                    skipped += 1
            else:
                # Case 2: Not completed (pending/failed) - always update
                supabase.from_('system.crawl_url').update({
                    'title': title,
                    'last_update_date': ngay_cap_nhat_parsed,
                    'status': 'pending'
                }).eq('url', url_str).execute()
                updated += 1
        else:
            # URL not exists - insert new
            supabase.from_('system.crawl_url').insert({
                'url': url_str,
                'doc_id': doc_id,
                'title': title,
                'last_update_date': ngay_cap_nhat_parsed,
                'status': 'pending',
                'priority': 0
            }).execute()
            inserted += 1
    
    return {
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped,
        'total': len(links)
    }

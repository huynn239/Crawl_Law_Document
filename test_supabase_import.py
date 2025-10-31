"""Test Supabase import"""
import json
import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def import_document(doc):
    """Import single document with version checking"""
    
    # 1. Insert/Update doc_urls
    result = supabase.from_('system.crawl_url').upsert({
        'url': doc['url'],
        'status': 'crawled'
    }, on_conflict='url').execute()
    
    doc_url_id = result.data[0]['id']
    
    # 2. Check latest version
    latest = supabase.table('doc_metadata')\
        .select('version, content_hash, ngay_cap_nhat')\
        .eq('doc_url_id', doc_url_id)\
        .order('version', desc=True)\
        .limit(1)\
        .execute()
    
    # 3. Decide
    should_insert = False
    
    if not latest.data:
        should_insert = True
        print(f"  → New document")
    else:
        latest_data = latest.data[0]
        if doc['content_hash'] != latest_data['content_hash']:
            should_insert = True
            print(f"  → Content changed")
        elif doc.get('ngay_cap_nhat') and doc['ngay_cap_nhat'] > latest_data.get('ngay_cap_nhat', ''):
            should_insert = True
            print(f"  → Date updated")
        else:
            print(f"  → No changes, skipped")
    
    # 4. Insert if needed
    if should_insert:
        supabase.table('doc_metadata').insert({
            'doc_url_id': doc_url_id,
            'so_hieu': doc.get('so_hieu'),
            'loai_van_ban': doc.get('loai_van_ban'),
            'linh_vuc': doc.get('linh_vuc'),
            'noi_ban_hanh': doc.get('noi_ban_hanh'),
            'nguoi_ky': doc.get('nguoi_ky'),
            'ngay_ban_hanh': doc.get('ngay_ban_hanh'),
            'ngay_hieu_luc': doc.get('ngay_hieu_luc'),
            'tinh_trang': doc.get('tinh_trang'),
            'extra_data': doc.get('extra_data'),
            'content_hash': doc['content_hash']
        }).execute()
        
        return True
    
    return False

def main():
    # Read transformed data
    file_path = Path('data/result_supabase.json')
    
    if not file_path.exists():
        print("❌ File not found. Run: python supabase_transform.py data/result.json")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    print(f"📦 Importing {len(documents)} documents...")
    
    inserted = 0
    skipped = 0
    
    for i, doc in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] {doc['url']}")
        
        try:
            if import_document(doc):
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ Done!")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped: {skipped}")

if __name__ == '__main__':
    main()

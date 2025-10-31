#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update missing target_doc_id in relationships table"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def update_missing_target_doc_ids():
    """Update target_doc_id for relationships where target document now exists"""
    
    print("🔍 Finding relationships with missing target_doc_id...")
    
    # Get relationships with NULL target_doc_id
    rels = supabase.table('relationships')\
        .select('id, target_doc_url')\
        .is_('target_doc_id', 'null')\
        .execute()
    
    total = len(rels.data)
    print(f"   Found: {total} relationships with NULL target_doc_id")
    
    if total == 0:
        print("✅ All relationships already have target_doc_id!")
        return
    
    print("\n🔄 Updating...")
    updated = 0
    not_found = 0
    
    for rel in rels.data:
        target_url = rel['target_doc_url']
        
        # Check if target document exists now
        doc_url = supabase.table('crawl_url')\
            .select('id')\
            .eq('url', target_url)\
            .execute()
        
        if doc_url.data:
            # Get latest doc_metadata
            target = supabase.table('doc_metadata')\
                .select('id')\
                .eq('doc_url_id', doc_url.data[0]['id'])\
                .order('version', desc=True)\
                .limit(1)\
                .execute()
            
            if target.data:
                # Update relationship
                supabase.table('relationships')\
                    .update({'target_doc_id': target.data[0]['id']})\
                    .eq('id', rel['id'])\
                    .execute()
                updated += 1
                print(f"   ✓ Updated relationship {rel['id']}")
            else:
                not_found += 1
        else:
            not_found += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total: {total}")
    print(f"   Updated: {updated}")
    print(f"   Not found: {not_found}")
    print(f"\n✅ Done!")

if __name__ == '__main__':
    update_missing_target_doc_ids()

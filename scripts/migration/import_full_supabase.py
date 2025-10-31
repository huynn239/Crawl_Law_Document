"""Import full data (metadata + relationships + files) to Supabase"""
import json
import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def import_metadata(metadata_list):
    """Import doc_metadata with version checking"""
    inserted = 0
    skipped = 0
    url_to_metadata_id = {}  # Cache mapping
    
    for doc in metadata_list:
        try:
            # 1. Upsert doc_urls
            result = supabase.table('crawl_url').upsert({
                'url': doc['url'],
                'status': 'crawled'
            }, on_conflict='url').execute()
            
            doc_url_id = result.data[0]['id']
            
            # 2. Check latest version
            latest = supabase.table('doc_metadata')\
                .select('content_hash')\
                .eq('doc_url_id', doc_url_id)\
                .order('version', desc=True)\
                .limit(1)\
                .execute()
            
            # 3. Insert if changed (trigger sẽ tự tăng version)
            if not latest.data or latest.data[0]['content_hash'] != doc['content_hash']:
                supabase.table('doc_metadata').insert({
                    'doc_url_id': doc_url_id,
                    'doc_id': doc.get('doc_id'),
                    'con_hieu_luc': doc.get('con_hieu_luc'),
                    'extra_data': doc.get('extra_data'),
                    'content_hash': doc['content_hash']
                }).execute()
                inserted += 1
                # Cache the new metadata_id
                url_to_metadata_id[doc['url']] = supabase.table('doc_metadata')\
                    .select('id').eq('doc_url_id', doc_url_id)\
                    .order('version', desc=True).limit(1).execute().data[0]['id']
            else:
                skipped += 1
                # Cache existing metadata_id
                url_to_metadata_id[doc['url']] = supabase.table('doc_metadata')\
                    .select('id').eq('doc_url_id', doc_url_id)\
                    .order('version', desc=True).limit(1).execute().data[0]['id']
        except Exception as e:
            print(f"  ⚠️  Error importing {doc.get('url')}: {e}")
            continue
    
    return inserted, skipped, url_to_metadata_id

def import_relationships(relationships_list, url_cache):
    """Import relationships using cached metadata IDs"""
    inserted = 0
    errors = 0
    
    for rel in relationships_list:
        try:
            source_url = rel.get('source_url')
            if not source_url or source_url not in url_cache:
                errors += 1
                continue
            
            source_doc_id = url_cache[source_url]
            
            # Get target_doc_id from cache if available
            target_doc_id = url_cache.get(rel.get('target_doc_url'))
            
            # Insert relationship (với UNIQUE constraint sẽ skip duplicate)
            supabase.table('relationships').insert({
                'source_doc_id': source_doc_id,
                'target_doc_url': rel['target_doc_url'],
                'target_doc_id': target_doc_id,
                'relationship_type': rel['relationship_type']
            }).execute()
            inserted += 1
        except Exception as e:
            errors += 1
    
    return inserted

def import_files(files_list, url_cache):
    """Import doc_files info using cached metadata IDs"""
    inserted = 0
    errors = 0
    
    for file in files_list:
        try:
            source_url = file.get('source_url')
            if not source_url or source_url not in url_cache:
                errors += 1
                continue
            
            doc_metadata_id = url_cache[source_url]
            
            # Insert file (UNIQUE constraint trên doc_metadata_id sẽ skip duplicate)
            supabase.table('doc_files').insert({
                'doc_metadata_id': doc_metadata_id,
                'file_name': file['file_name'],
                'file_type': file['file_type'],
                'local_path': file.get('file_url', '')  # Store URL as local_path for now
            }).execute()
            inserted += 1
        except Exception as e:
            errors += 1
    
    return inserted

def update_missing_target_doc_ids():
    """Update target_doc_id for relationships where target document now exists"""
    print("\n[4/4] Updating missing target_doc_id...")
    
    # Get relationships with NULL target_doc_id
    rels = supabase.table('relationships')\
        .select('id, target_doc_url')\
        .is_('target_doc_id', 'null')\
        .execute()
    
    updated = 0
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
    
    print(f"  Updated: {updated}")
    return updated

def main():
    import sys
    
    # Cho phép truyền file path qua argument
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
    else:
        file_path = Path('data/resultTest_supabase.json')  # Default file
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        print("Run: python supabase_transform.py data/result.json")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("Importing to Supabase...")
    
    # 1. Import metadata
    print("\n[1/4] Importing metadata...")
    inserted, skipped, url_cache = import_metadata(data['doc_metadata'])
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    
    # 2. Import relationships
    print("\n[2/4] Importing relationships...")
    rel_count = import_relationships(data['relationships'], url_cache)
    print(f"  Inserted: {rel_count}")
    
    # 3. Import files
    print("\n[3/4] Importing files...")
    file_count = import_files(data['doc_files'], url_cache)
    print(f"  Inserted: {file_count}")
    
    # 4. Update missing target_doc_id
    update_missing_target_doc_ids()
    
    print("\nDone!")

if __name__ == '__main__':
    main()

"""Verify data in Supabase"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=== SUPABASE DATA SUMMARY ===\n")

# Count records
urls = supabase.from_('system.crawl_url').select('*', count='exact').execute()
print(f"doc_urls: {urls.count} records")

metadata = supabase.table('doc_metadata').select('*', count='exact').execute()
print(f"doc_metadata: {metadata.count} records")

relationships = supabase.table('relationships').select('*', count='exact').execute()
print(f"relationships: {relationships.count} records")

files = supabase.table('doc_files').select('*', count='exact').execute()
print(f"doc_files: {files.count} records")

# Sample data
print("\n=== SAMPLE METADATA ===")
sample = supabase.table('doc_metadata').select('doc_id, so_hieu, loai_van_ban').limit(3).execute()
for doc in sample.data:
    print(f"  {doc['doc_id']}: {doc['so_hieu']} ({doc['loai_van_ban']})")

print("\n=== SAMPLE RELATIONSHIPS ===")
sample_rel = supabase.table('relationships').select('source_doc_id, target_doc_id, relationship_type').limit(3).execute()
for rel in sample_rel.data:
    print(f"  {rel['source_doc_id']} -> {rel['target_doc_id']} ({rel['relationship_type']})")

print("\n=== SAMPLE FILES ===")
sample_files = supabase.table('doc_files').select('doc_metadata_id, file_name, file_type').limit(3).execute()
for f in sample_files.data:
    print(f"  Doc {f['doc_metadata_id']}: {f['file_name']} ({f['file_type']})")

print("\nDone!")

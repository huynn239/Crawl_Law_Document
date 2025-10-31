"""Import to Supabase with PostgreSQL logic (version tracking + smart merge)"""
import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def compute_hash(data: dict) -> str:
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()

def parse_date(date_str: str):
    if not date_str:
        return None
    # Try ISO format first (YYYY-MM-DD)
    if len(date_str) == 10 and date_str[4] == '-':
        return date_str
    # Try dd/mm/yyyy format
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return None

def compute_diff(old_data: dict, new_data: dict) -> dict:
    diff = {"changed_fields": [], "relations_added": 0, "relations_removed": 0}
    
    old_info = old_data.get("doc_info", {})
    new_info = new_data.get("doc_info", {})
    for key in new_info:
        if old_info.get(key) != new_info.get(key):
            diff["changed_fields"].append(key)
    
    old_rels = old_data.get("tab4", {}).get("relations", {})
    new_rels = new_data.get("tab4", {}).get("relations", {})
    old_total = sum(len(v) for v in old_rels.values())
    new_total = sum(len(v) for v in new_rels.values())
    diff["relations_added"] = max(0, new_total - old_total)
    diff["relations_removed"] = max(0, old_total - new_total)
    
    return diff if diff["changed_fields"] or diff["relations_added"] or diff["relations_removed"] else None

def start_session():
    result = supabase.table('crawl_sessions').insert({
        'status': 'RUNNING'
    }).execute()
    return result.data[0]['session_id']

def complete_session(session_id, total, new_versions, unchanged):
    supabase.table('crawl_sessions').update({
        'status': 'COMPLETED',
        'completed_at': datetime.now().isoformat(),
        'total_docs': total,
        'new_versions': new_versions,
        'unchanged_docs': unchanged
    }).eq('session_id', session_id).execute()

def save_document(data: dict, session_id: int):
    url = data.get("url", "")
    doc_id = url.split("-")[-1].replace(".aspx", "") if url else None
    if not doc_id:
        return False
    
    # Handle failed documents
    if data.get("error"):
        supabase.table('crawl_url').update({
            'status': 'failed',
            'last_attempt_at': datetime.now().isoformat(),
            'error_message': data.get("error", "")[:500]
        }).eq('url', url).execute()
        return False
    
    # Priority: title (from input) > so_hieu (from crawl) > Untitled
    title = (
        data.get("title") or 
        data.get("doc_info", {}).get("so_hieu", "") or 
        "Untitled"
    )
    
    # 1. Upsert doc_urls
    supabase.table('crawl_url').upsert({
        'url': url,
        'doc_id': doc_id,
        'title': title,
        'status': 'completed',
        'last_attempt_at': datetime.now().isoformat()
    }, on_conflict='url').execute()
    update_date = parse_date(data.get("ngay_cap_nhat", ""))
    metadata = data.get("doc_info", {})
    
    download_link = ""
    tab8_links = data.get("tab8", {}).get("links", [])
    if tab8_links:
        download_link = tab8_links[0].get("href", "")
    
    important_data = {
        "doc_info": data.get("doc_info", {}),
        "tab4": data.get("tab4", {}),
        "tab8": data.get("tab8", {})
    }
    content_hash = compute_hash(important_data)
    
    # Check existing
    existing = supabase.table('document_finals').select('hash, update_date').eq('doc_id', doc_id).execute()
    old_hash = existing.data[0]['hash'] if existing.data else None
    old_update_date = existing.data[0]['update_date'] if existing.data else None
    
    has_changed = (
        old_hash is None or 
        old_hash != content_hash or
        (update_date and old_update_date and update_date > old_update_date)
    )
    
    # Smart merge: fallback to old tab4 if new is empty
    if has_changed and old_hash:
        new_total = data.get("tab4", {}).get("total", 0)
        if new_total == 0:
            old_version = supabase.table('document_versions')\
                .select('content').eq('doc_id', doc_id)\
                .order('crawled_at', desc=True).limit(1).execute()
            if old_version.data:
                old_tab4 = old_version.data[0]['content'].get("tab4", {})
                old_total = old_tab4.get("total", 0)
                if old_total > 0:
                    data["tab4"] = old_tab4
                    print(f"    ↻ Fallback to old tab4 ({old_total} relations)")
    
    if has_changed:
        # Upsert documents_finals
        supabase.table('document_finals').upsert({
            'doc_id': doc_id,
            'title': title,
            'url': url,
            'hash': content_hash,
            'update_date': update_date,
            'metadata': metadata,
            'download_link': download_link,
            'relations_summary': data.get('tab4', {}).get('summary', {}),
            'last_crawled': datetime.now().isoformat()
        }, on_conflict='doc_id').execute()
        
        # Insert version
        diff_summary = None
        if old_hash:
            old_version = supabase.table('document_versions')\
                .select('content').eq('doc_id', doc_id)\
                .order('crawled_at', desc=True).limit(1).execute()
            if old_version.data:
                diff_summary = compute_diff(old_version.data[0]['content'], data)
        
        compact_content = {
            "doc_info": data.get("doc_info", {}),
            "tab4": data.get("tab4", {})
        }
        
        supabase.table('document_versions').insert({
            'doc_id': doc_id,
            'version_hash': content_hash,
            'content': compact_content,
            'session_id': session_id,
            'diff_summary': diff_summary,
            'source_snapshot_date': update_date
        }).execute()
        
        # Delete old relations
        supabase.table('document_relations').delete().eq('source_doc_id', doc_id).execute()
        
        # Insert new relations
        tab4 = data.get("tab4", {})
        relations = tab4.get("relations", {})
        
        for relation_type, targets in relations.items():
            if not targets:
                continue
            for target in targets:
                target_url = target.get("href", "")
                target_title = target.get("text", "")
                target_doc_id = target_url.split("-")[-1].replace(".aspx", "") if target_url else None
                
                supabase.table('document_relations').insert({
                    'source_doc_id': doc_id,
                    'relation_type': relation_type,
                    'target_doc_id': target_doc_id,
                    'target_url': target_url,
                    'target_title': target_title,
                    'resolved': bool(target_doc_id)
                }).execute()
        
        # Save document_files
        tab8_links = data.get("tab8", {}).get("links", [])
        if tab8_links:
            # Delete old files
            supabase.table('document_files').delete().eq('doc_id', doc_id).execute()
            
            # Insert new files
            for link in tab8_links:
                file_url = link.get("href", "")
                file_name = link.get("text", "")
                file_text = file_name.lower()
                
                # Detect file type
                if "pdf" in file_text:
                    file_type = "pdf"
                elif "docx" in file_text:
                    file_type = "docx"
                elif "doc" in file_text:
                    file_type = "doc"
                elif "tải văn bản tiếng việt" in file_text or "tai van ban tieng viet" in file_text:
                    file_type = "doc"
                else:
                    file_type = "other"
                
                supabase.table('document_files').insert({
                    'doc_id': doc_id,
                    'file_name': file_name,
                    'file_type': file_type,
                    'file_url': file_url,
                    'download_status': 'pending'
                }).execute()
    else:
        # Update last_crawled and title
        supabase.table('document_finals').update({
            'title': title,
            'last_crawled': datetime.now().isoformat()
        }).eq('doc_id', doc_id).execute()
    
    return has_changed

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_supabase_v2.py <json_file>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Importing {len(data)} documents to Supabase...")
    
    session_id = start_session()
    print(f"✓ Session #{session_id}")
    
    new_versions = 0
    unchanged = 0
    errors = 0
    
    for item in data:
        if item.get("error"):
            continue
        try:
            has_changed = save_document(item, session_id)
            if has_changed:
                new_versions += 1
                print(f"  ✓ {item['doc_info'].get('so_hieu', 'N/A')} - Changed")
            else:
                unchanged += 1
                print(f"  - {item['doc_info'].get('so_hieu', 'N/A')} - Unchanged")
        except Exception as e:
            errors += 1
            print(f"  ✗ {item.get('url', '')}: {e}")
    
    complete_session(session_id, len(data), new_versions, unchanged)
    print(f"\n✓ Done: {new_versions} changed, {unchanged} unchanged, {errors} errors")

if __name__ == '__main__':
    main()

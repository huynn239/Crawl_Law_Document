#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download files và upload lên Supabase Storage"""
import os
import requests
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import hashlib

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def download_file(url: str, save_path: Path) -> bool:
    """Download file từ URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return False

def upload_to_supabase_storage(file_path: Path, bucket: str = 'documents') -> str:
    """Upload file lên Supabase Storage"""
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Generate unique filename
        file_hash = hashlib.md5(file_data).hexdigest()[:8]
        storage_path = f"{file_path.stem}_{file_hash}{file_path.suffix}"
        
        # Upload
        supabase.storage.from_(bucket).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(storage_path)
        
        return public_url
    except Exception as e:
        print(f"  ❌ Upload failed: {e}")
        return None

def process_pending_files():
    """Download và upload files chưa xử lý"""
    
    print("🔍 Finding files to download...")
    
    # Get files chưa download (local_path là URL)
    files = supabase.table('doc_files')\
        .select('id, file_name, file_type, local_path')\
        .like('local_path', 'http%')\
        .execute()
    
    total = len(files.data)
    print(f"   Found: {total} files")
    
    if total == 0:
        print("✅ All files already processed!")
        return
    
    print("\n📥 Downloading and uploading...")
    
    success = 0
    failed = 0
    temp_dir = Path('data/temp_downloads')
    
    for file in files.data:
        file_url = file['local_path']
        file_name = file['file_name']
        file_type = file['file_type']
        
        print(f"\n  Processing: {file_name}")
        
        # Download
        temp_file = temp_dir / f"{file['id']}.{file_type}"
        if not download_file(file_url, temp_file):
            failed += 1
            continue
        
        # Upload to Supabase Storage
        storage_url = upload_to_supabase_storage(temp_file)
        if not storage_url:
            failed += 1
            continue
        
        # Update database
        supabase.table('doc_files')\
            .update({
                'local_path': storage_url,
                'file_size': temp_file.stat().st_size
            })\
            .eq('id', file['id'])\
            .execute()
        
        # Cleanup temp file
        temp_file.unlink()
        
        success += 1
        print(f"  ✅ Uploaded to: {storage_url}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total: {total}")
    print(f"   Success: {success}")
    print(f"   Failed: {failed}")

if __name__ == '__main__':
    process_pending_files()

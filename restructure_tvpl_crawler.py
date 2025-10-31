import os
import shutil

# Mapping files to new structure
TVPL_STRUCTURE = {
    'tvpl_crawler/core/': [
        'config.py', 'db.py', 'storage.py', 'parser.py', 
        'http_client.py', 'tnpl_db.py'
    ],
    'tvpl_crawler/crawlers/': [
        'crawl_data_fast.py', 'crawl_pending.py', 'crawl_selenium.py',
        'links_playwright.py', 'fetch_pending_urls.py', 
        'download_files_playwright.py'
    ],
    'tvpl_crawler/crawlers/playwright/': [
        'playwright_extract.py', 'playwright_extract_async.py',
        'playwright_extract_simple.py', 'playwright_login.py'
    ],
    'tvpl_crawler/crawlers/selenium/': [
        'selenium_extract.py'
    ],
    'tvpl_crawler/extractors/': [
        'formula_extractor.py'
    ],
    'tvpl_crawler/utils/': [
        'captcha_solver.py', 'cleanup_sessions.py', 'compact_schema.py',
        'import_supabase_v2.py', 'upsert_links.py'
    ]
}

def create_init_files():
    """Tạo __init__.py cho các folders mới"""
    folders = [
        'tvpl_crawler/core',
        'tvpl_crawler/crawlers',
        'tvpl_crawler/crawlers/playwright',
        'tvpl_crawler/crawlers/selenium',
        'tvpl_crawler/extractors',
        'tvpl_crawler/utils'
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        init_file = os.path.join(folder, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(f'"""{"".join(folder.split("/")[-1]).title()} module"""\n')

def move_files():
    """Di chuyển files vào cấu trúc mới"""
    moved = []
    
    for target_dir, files in TVPL_STRUCTURE.items():
        os.makedirs(target_dir, exist_ok=True)
        
        for filename in files:
            src = os.path.join('tvpl_crawler', filename)
            dest = os.path.join(target_dir, filename)
            
            if os.path.exists(src) and not os.path.exists(dest):
                try:
                    shutil.move(src, dest)
                    moved.append(f"{src} → {dest}")
                except Exception as e:
                    print(f"Error moving {src}: {e}")
    
    return moved

def fix_imports_in_file(filepath):
    """Fix imports trong 1 file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Fix imports từ tvpl_crawler
        replacements = {
            'from tvpl_crawler.core.config import': 'from tvpl_crawler.core.config import',
            'from tvpl_crawler.core.db import': 'from tvpl_crawler.core.db import',
            'from tvpl_crawler.core.storage import': 'from tvpl_crawler.core.storage import',
            'from tvpl_crawler.core.parser import': 'from tvpl_crawler.core.parser import',
            'from tvpl_crawler.core.http_client import': 'from tvpl_crawler.core.http_client import',
            'from tvpl_crawler.core.tnpl_db import': 'from tvpl_crawler.core.tnpl_db import',
            
            'from tvpl_crawler.extractors.formula_extractor import': 'from tvpl_crawler.extractors.formula_extractor import',
            
            'from tvpl_crawler.utils.captcha_solver import': 'from tvpl_crawler.utils.captcha_solver import',
            'from tvpl_crawler.utils.cleanup_sessions import': 'from tvpl_crawler.utils.cleanup_sessions import',
            
            'from tvpl_crawler.crawlers.crawl_data_fast import': 'from tvpl_crawler.crawlers.crawl_data_fast import',
            'from tvpl_crawler.crawlers.crawl_pending import': 'from tvpl_crawler.crawlers.crawl_pending import',
            
            'from tvpl_crawler.crawlers.playwright.extract import': 'from tvpl_crawler.crawlers.playwright.extract import',
            'from tvpl_crawler.crawlers.playwright.login import': 'from tvpl_crawler.crawlers.playwright.login import',
            
            # Relative imports trong tvpl_crawler
            'from .core.config import': 'from .core.config import',
            'from .core.db import': 'from .core.db import',
            'from .core.storage import': 'from .core.storage import',
            'from .core.parser import': 'from .core.parser import',
            'from .core.http_client import': 'from .core.http_client import',
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Fix imports trong tvpl_crawler subfolders
        if filepath.startswith('tvpl_crawler'):
            # Trong core/ import lẫn nhau
            if 'tvpl_crawler/core/' in filepath or 'tvpl_crawler\\core\\' in filepath:
                content = content.replace('from config import', 'from .core.config import')
                content = content.replace('from db import', 'from .core.db import')
                content = content.replace('from storage import', 'from .core.storage import')
            
            # Trong crawlers/ import từ core
            if 'tvpl_crawler/crawlers/' in filepath or 'tvpl_crawler\\crawlers\\' in filepath:
                content = content.replace('from config import', 'from ..core.config import')
                content = content.replace('from db import', 'from ..core.db import')
                content = content.replace('from storage import', 'from ..core.storage import')
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def fix_all_imports():
    """Fix imports trong tất cả files"""
    fixed = []
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', 'data', 'archive']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_imports_in_file(filepath):
                    fixed.append(filepath)
    
    return fixed

if __name__ == '__main__':
    print("Restructuring tvpl_crawler...")
    
    # Step 1: Create folders and __init__.py
    print("\n1. Creating folders...")
    create_init_files()
    
    # Step 2: Move files
    print("\n2. Moving files...")
    moved = move_files()
    print(f"OK Moved {len(moved)} files")
    for m in moved[:10]:
        print(f"  {m}")
    if len(moved) > 10:
        print(f"  ... and {len(moved)-10} more")
    
    # Step 3: Fix imports
    print("\n3. Fixing imports...")
    fixed = fix_all_imports()
    print(f"OK Fixed imports in {len(fixed)} files")
    for f in fixed[:10]:
        print(f"  {f}")
    if len(fixed) > 10:
        print(f"  ... and {len(fixed)-10} more")
    
    print("\nOK Restructure complete!")
    print("\nNext: Run 'python test_imports.py' to verify")

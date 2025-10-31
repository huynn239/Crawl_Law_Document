import os
import re

# Import mappings sau khi restructure
IMPORT_FIXES = {
    # Scripts đã di chuyển vào scripts/
    r'from scripts.crawl.crawl_': 'from scripts.crawl.crawl_',
    r'from scripts.test.test_': 'from scripts.test.test_',
    r'from scripts.test.debug_': 'from scripts.test.debug_',
    r'from scripts.crawl from scripts.crawl import crawl_': 'from scripts.crawl from scripts.crawl from scripts.crawl import crawl_',
    r'from scripts.test from scripts.test import test_': 'from scripts.test from scripts.test from scripts.test import test_',
    
    # Extractors
    r'from (\w+_extractor) import': r'from scripts.extract.\1 import',
    r'import (\w+_extractor)': r'from scripts.extract import \1',
    
    # Migration scripts
    r'from (migrate_|import_|export_|transform_|backup_)': r'from scripts.migration.\1',
    
    # Utils
    r'from (setup_|cleanup_|clear_)': r'from scripts.utils.\1',
    
    # Config - giữ nguyên vì ở root
    r'from config import': 'from config import',
    r'import config': 'import config',
}

def fix_file_imports(filepath):
    """Fix imports trong 1 file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Apply fixes
        for pattern, replacement in IMPORT_FIXES.items():
            content = re.sub(pattern, replacement, content)
        
        # Fix relative imports trong scripts/
        if filepath.startswith('scripts'):
            # Nếu file trong scripts/crawl/ import từ scripts/utils/
            content = re.sub(r'from utils\.', 'from scripts.utils.', content)
            content = re.sub(r'from \.\.utils\.', 'from scripts.utils.', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def scan_and_fix():
    """Scan tất cả Python files và fix imports"""
    fixed = []
    
    for root, dirs, files in os.walk('.'):
        # Skip venv, __pycache__, .git
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', 'data', 'archive', 'build', 'dist']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file_imports(filepath):
                    fixed.append(filepath)
    
    return fixed

if __name__ == '__main__':
    print("Fixing imports after restructure...")
    fixed = scan_and_fix()
    
    if fixed:
        print(f"\n✓ Fixed imports in {len(fixed)} files:")
        for f in fixed[:20]:
            print(f"  - {f}")
        if len(fixed) > 20:
            print(f"  ... and {len(fixed)-20} more")
    else:
        print("\n✓ No imports need fixing (or already fixed)")
    
    print("\n⚠️  Manual check needed for:")
    print("  - Circular imports")
    print("  - Dynamic imports")
    print("  - Imports in __init__.py files")

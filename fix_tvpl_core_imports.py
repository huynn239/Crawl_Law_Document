"""Fix imports trong tvpl_crawler/core/"""
import os
import re

def fix_file(filepath):
    """Fix imports trong 1 file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Fix: from .core.xxx -> from .xxx (vì đã ở trong core/ rồi)
        content = re.sub(r'from \.core\.(\w+) import', r'from .\1 import', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False

# Fix all files in tvpl_crawler/core/
fixed = []
core_dir = 'tvpl_crawler/core'

if os.path.exists(core_dir):
    for file in os.listdir(core_dir):
        if file.endswith('.py'):
            filepath = os.path.join(core_dir, file)
            if fix_file(filepath):
                fixed.append(filepath)

print(f"Fixed {len(fixed)} files:")
for f in fixed:
    print(f"  - {f}")

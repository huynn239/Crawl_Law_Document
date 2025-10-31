"""Revert supabase queries về dùng table names thông thường"""
import os
import re

def fix_file(filepath):
    """Revert supabase queries"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Revert: supabase.table('table') -> supabase.table('table')
        content = re.sub(r"supabase\.schema\('[^']+'\)\.from_\('([^']+)'\)", r"supabase.table('\1')", content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False

# Scan all Python files
fixed = []

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', 'data', 'archive']]
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            if fix_file(filepath):
                fixed.append(filepath)

print(f"Reverted {len(fixed)} files:")
for f in fixed:
    print(f"  - {f}")

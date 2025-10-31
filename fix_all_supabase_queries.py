"""Fix all supabase queries to use .schema().from_()"""
import os
import re

def fix_file(filepath):
    """Fix supabase queries trong 1 file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Fix: supabase.from_('schema.table') -> supabase.table('table')
        replacements = {
            r"supabase\.from_\('tvpl\.(\w+)'\)": r"supabase.table('\1')",
            r"supabase\.from_\('tnpl\.(\w+)'\)": r"supabase.table('\1')",
            r"supabase\.from_\('system\.(\w+)'\)": r"supabase.table('\1')",
            r"supabase\.from_\('views\.(\w+)'\)": r"supabase.table('\1')",
        }
        
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
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

print(f"Fixed {len(fixed)} files:")
for f in fixed:
    print(f"  - {f}")

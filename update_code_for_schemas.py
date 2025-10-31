import os
import re

# Mapping table names
REPLACEMENTS = {
    # TVPL schema
    r"\.table\(['\"]documents_finals['\"]\)": ".from_('tvpl.document_finals')",
    r"\.table\(['\"]document_relations['\"]\)": ".from_('tvpl.document_relations')",
    r"\.table\(['\"]document_files['\"]\)": ".from_('tvpl.document_files')",
    r"\.table\(['\"]document_versions['\"]\)": ".from_('tvpl.document_versions')",
    
    # SYSTEM schema
    r"\.table\(['\"]doc_urls['\"]\)": ".from_('system.crawl_url')",
    r"\.table\(['\"]crawl_sessions['\"]\)": ".from_('system.crawl_sessions')",
    
    # TNPL schema
    r"\.table\(['\"]tnpl_terms['\"]\)": ".from_('tnpl.terms')",
    r"\.table\(['\"]tnpl_crawl_sessions['\"]\)": ".from_('tnpl.crawl_sessions')",
}

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for pattern, replacement in REPLACEMENTS.items():
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Scan Python files
updated = []
for root, dirs, files in os.walk('.'):
    if 'venv' in root or '__pycache__' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            if update_file(filepath):
                updated.append(filepath)

print(f"✓ Updated {len(updated)} files:")
for f in updated:
    print(f"  - {f}")

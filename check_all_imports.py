"""Check tất cả imports trong project"""
import os
import re

def check_file(filepath):
    """Check imports trong 1 file"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check các pattern có thể sai
        patterns = [
            (r'from \.core\.core\.', 'Double .core.core'),
            (r'from \.crawlers\.crawlers\.', 'Double .crawlers.crawlers'),
            (r'from \.utils\.utils\.', 'Double .utils.utils'),
            (r'from \.extractors\.extractors\.', 'Double .extractors.extractors'),
        ]
        
        for pattern, desc in patterns:
            if re.search(pattern, content):
                issues.append(f"{desc}: {pattern}")
        
        # Check imports trong tvpl_crawler/core/ không nên có .core.
        if 'tvpl_crawler/core/' in filepath.replace('\\', '/') or 'tvpl_crawler\\core\\' in filepath:
            if re.search(r'from \.core\.', content):
                issues.append("In core/ but imports from .core.")
        
        # Check imports trong tvpl_crawler/crawlers/ không nên có .crawlers.
        if 'tvpl_crawler/crawlers/' in filepath.replace('\\', '/') or 'tvpl_crawler\\crawlers\\' in filepath:
            if re.search(r'from \.crawlers\.', content):
                issues.append("In crawlers/ but imports from .crawlers.")
        
        return issues
    except Exception as e:
        return [f"Error reading: {e}"]

# Scan all Python files
all_issues = {}

for root, dirs, files in os.walk('.'):
    # Skip venv, __pycache__, etc
    dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git', 'node_modules', 'data', 'archive']]
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            issues = check_file(filepath)
            if issues:
                all_issues[filepath] = issues

if all_issues:
    print(f"Found {len(all_issues)} files with potential import issues:\n")
    for filepath, issues in all_issues.items():
        print(f"{filepath}:")
        for issue in issues:
            print(f"  - {issue}")
        print()
else:
    print("OK No import issues found!")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restructure script - Tái cấu trúc project"""
import os
import shutil
import sys

def restructure_project():
    """Tái cấu trúc project theo logic mới"""
    
    print("RESTRUCTURING PROJECT...")
    
    # 1. Di chuyển core files
    moves = [
        # Core extractors
        ('production_ready_extractor.py', 'core/extractors/production_extractor.py'),
        ('enhanced_regex_patterns.py', 'core/patterns/regex_patterns.py'),
        ('smart_formula_separator.py', 'core/extractors/formula_separator.py'),
        
        # Scripts
        ('crawl_formulas_fast.py', 'scripts/crawl/crawl_formulas.py'),
        ('setup_database.py', 'scripts/utils/setup_db.py'),
        
        # Documentation
        ('README.md', 'docs/README.md'),
        ('FORMULA_EXTRACTION_REPORT.md', 'docs/EXTRACTION_GUIDE.md'),
    ]
    
    for src, dst in moves:
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            print(f"Moved {src} -> {dst}")
        else:
            print(f"WARNING: {src} not found")
    
    # 2. Tạo __init__.py files
    init_files = [
        'core/__init__.py',
        'core/extractors/__init__.py', 
        'core/patterns/__init__.py',
        'core/filters/__init__.py',
        'scripts/__init__.py',
        'scripts/crawl/__init__.py',
        'scripts/test/__init__.py',
        'scripts/utils/__init__.py'
    ]
    
    for init_file in init_files:
        os.makedirs(os.path.dirname(init_file), exist_ok=True)
        with open(init_file, 'w') as f:
            f.write('# -*- coding: utf-8 -*-\n')
        print(f"Created {init_file}")
    
    # 3. Tạo main.py entry point
    main_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main entry point for thuvienphapluat-crawler"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.extractors.production_extractor import ProductionReadyExtractor

def main():
    """Main function"""
    print("Thuvienphapluat Crawler")
    print("Available commands:")
    print("  python scripts/crawl/crawl_formulas.py - Crawl formulas")
    print("  python scripts/utils/setup_db.py - Setup database")
    
    # Example usage
    extractor = ProductionReadyExtractor()
    sample_text = "Tiền lương = Hệ số × 1.800.000 đồng"
    result = extractor.extract_from_text(sample_text)
    print(f"Sample extraction: {result['total_formulas']} formulas found")

if __name__ == "__main__":
    main()
'''
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(main_content)
    print("Created main.py")
    
    # 4. Tạo document filter
    filter_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Document Filter - Pre-filtering for documents"""
import re

class DocumentFilter:
    def __init__(self):
        self.formula_indicators = [r'=', r'×|÷|\\*|/|%', r'[0-9.,]+\\s*%', r'[0-9.,]+\\s*đồng']
        self.exclude_patterns = [r'^\\s*điều\\s+\\d+', r'liên hệ|email|website']
    
    def has_formulas(self, content: str) -> bool:
        if not content or len(content) < 50:
            return False
        indicator_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in self.formula_indicators)
        exclusion_count = sum(1 for p in self.exclude_patterns if re.search(p, content, re.IGNORECASE))
        return (indicator_count - exclusion_count * 2) >= 1
'''
    
    with open('core/filters/document_filter.py', 'w', encoding='utf-8') as f:
        f.write(filter_content)
    print("Created core/filters/document_filter.py")
    
    # 5. Cleanup - xóa folder formula_extraction
    if os.path.exists('formula_extraction'):
        shutil.rmtree('formula_extraction')
        print("Removed formula_extraction/ folder")
    
    # 6. Xóa các file test duplicate
    test_files_to_remove = [
        'update_crawl_formulas.py',
        'test_real_url.py',
        'test_real_content.py',
        'final_comparison.py',
        'run_improved_audit.py'
    ]
    
    for file in test_files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed {file}")
    
    print("\nRESTRUCTURE COMPLETED!")
    print("New structure:")
    print("   core/ - Core functionality")
    print("   scripts/ - Executable scripts") 
    print("   data/ - Data storage")
    print("   docs/ - Documentation")
    print("   main.py - Entry point")

if __name__ == "__main__":
    restructure_project()
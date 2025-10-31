#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test với existing crawl script"""
import sys
import os
import json
from scripts.extract.production_ready_extractor import ProductionReadyExtractor
from scripts.extract.improved_llm_extractor import ImprovedLLMExtractorV21

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def test_with_crawl_script():
    """Test bằng cách sử dụng crawl script có sẵn"""
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("🧪 TESTING WITH EXISTING CRAWL PIPELINE")
    print("=" * 70)
    print(f"URL: {url}")
    print()
    
    # Tạo file input cho crawl script
    test_links = [{"Stt": 1, "Tên văn bản": "Thông tư 21/2025", "Url": url}]
    
    input_file = "data/test_single_link.json"
    os.makedirs("data", exist_ok=True)
    
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(test_links, f, ensure_ascii=False, indent=2)
    
    print(f"📝 Created test input: {input_file}")
    
    # Chạy crawl_formulas_fast.py
    print("🚀 Running crawl_formulas_fast.py...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, "crawl_formulas_fast.py", 
        input_file, 
        "data/test_formula_output.json",
        "playwright"
    ], capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print("✅ Crawl completed successfully")
        
        # Load và analyze kết quả
        try:
            with open("data/test_formula_output.json", "r", encoding="utf-8") as f:
                crawl_results = json.load(f)
            
            if crawl_results:
                doc = crawl_results[0]
                
                print(f"\n📊 CRAWL RESULTS:")
                print(f"   URL: {doc.get('url', 'N/A')}")
                print(f"   Tab1 formulas: {doc.get('tab1', {}).get('total_formulas', 0)}")
                
                # Test với improved extractors trên nội dung đã crawl
                if 'tab1' in doc and 'content' in doc['tab1']:
                    content = doc['tab1']['content']
                    
                    print(f"\n🧮 TESTING IMPROVED EXTRACTORS:")
                    print(f"   Content length: {len(content):,} chars")
                    
                    # Test Regex
                    regex_extractor = ProductionReadyExtractor()
                    regex_result = regex_extractor.extract_from_text(content)
                    
                    print(f"   Regex formulas: {regex_result['total_formulas']}")
                    print(f"   Regex parameters: {regex_result['total_parameters']}")
                    
                    # Test LLM
                    llm_extractor = ImprovedLLMExtractorV21()
                    llm_result = llm_extractor.extract_with_improved_prompt(content)
                    
                    print(f"   LLM formulas: {llm_result['total_formulas']}")
                    
                    total = regex_result['total_formulas'] + llm_result['total_formulas']
                    print(f"   🚀 Combined total: {total}")
                    
                    # Show samples
                    print(f"\n📝 SAMPLE RESULTS:")
                    for i, f in enumerate(regex_result['formulas'][:2], 1):
                        print(f"   {i}. [REGEX] {f['name']}: {f['formula'][:50]}...")
                    
                    for i, f in enumerate(llm_result['formulas'][:2], len(regex_result['formulas'][:2])+1):
                        print(f"   {i}. [LLM] {f['name']}: {f['formula'][:50]}...")
                
        except Exception as e:
            print(f"❌ Error loading results: {e}")
    
    else:
        print(f"❌ Crawl failed: {result.stderr}")
    
    print(f"\n✅ TEST COMPLETED!")

if __name__ == "__main__":
    test_with_crawl_script()
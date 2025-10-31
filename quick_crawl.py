#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick Crawl - Crawl nhanh để lấy công thức"""
import sys
import os
import json
from playwright.sync_api import sync_playwright
from core.extractors.production_extractor import ProductionReadyExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def crawl_single_url(url: str) -> dict:
    """Crawl 1 URL và extract formulas"""
    
    print(f"Crawling: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to URL
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle')
            
            # Get tab1 content
            content = ""
            selectors = ['#tab1 .noidung', '.noidung', '#divContent', '.content-detail']
            
            for selector in selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        content = element.inner_text()
                        break
                except:
                    continue
            
            if not content:
                content = page.inner_text('body')
            
            print(f"Content length: {len(content):,} chars")
            
            # Extract formulas
            extractor = ProductionReadyExtractor()
            result = extractor.extract_from_text(content)
            
            return {
                'url': url,
                'content_length': len(content),
                'formulas': result['formulas'],
                'parameters': result['parameters'],
                'total_formulas': result['total_formulas'],
                'total_parameters': result['total_parameters'],
                'extraction_method': result['extraction_method'],
                'filter_applied': result.get('filter_applied', False)
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'parameters': [],
                'total_formulas': 0,
                'total_parameters': 0
            }
        finally:
            browser.close()

def crawl_from_file(input_file: str, output_file: str):
    """Crawl từ file links"""
    
    print(f"QUICK CRAWL - Formula Extraction")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print("=" * 50)
    
    # Load links
    with open(input_file, 'r', encoding='utf-8') as f:
        links = json.load(f)
    
    results = []
    
    for i, link in enumerate(links, 1):
        url = link.get('Url', '')
        title = link.get('Tên văn bản', f'Document {i}')
        
        print(f"\n{i}/{len(links)}: {title}")
        
        result = crawl_single_url(url)
        result['stt'] = i
        result['title'] = title
        
        results.append(result)
        
        # Show summary
        if result.get('filter_applied'):
            print(f"   Status: FILTERED (no formulas)")
        else:
            print(f"   Formulas: {result['total_formulas']}")
            print(f"   Parameters: {result['total_parameters']}")
    
    # Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Summary
    total_formulas = sum(r['total_formulas'] for r in results)
    total_parameters = sum(r['total_parameters'] for r in results)
    filtered_count = sum(1 for r in results if r.get('filter_applied'))
    
    print(f"\nSUMMARY:")
    print(f"   Documents processed: {len(results)}")
    print(f"   Documents filtered: {filtered_count}")
    print(f"   Total formulas: {total_formulas}")
    print(f"   Total parameters: {total_parameters}")
    print(f"   Results saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python quick_crawl.py <input_links.json> <output_results.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    crawl_from_file(input_file, output_file)
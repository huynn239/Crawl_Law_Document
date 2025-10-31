#!/usr/bin/env python3
"""
Crawl tab1 content only
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright
import os

async def crawl_tab1_content():
    """Crawl only tab1 content from the education document"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # Load cookies if available
        cookies_file = "data/cookies.json"
        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("Loaded cookies")
            except:
                print("No cookies loaded")
        
        page = await context.new_page()
        
        try:
            print(f"Loading: {url}")
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            
            # Click tab1 to ensure content is loaded
            await page.evaluate("""
                () => {
                    const tab1Link = document.querySelector('a[href="#tab1"]');
                    if (tab1Link) {
                        tab1Link.click();
                    }
                }
            """)
            
            await page.wait_for_timeout(2000)
            
            # Extract tab1 content
            tab1_content = await page.evaluate("""
                () => {
                    const tab1 = document.querySelector('#tab1');
                    if (tab1) {
                        return tab1.innerText;
                    }
                    
                    // Fallback: get main content
                    const contentDiv = document.querySelector('#ctl00_Content_divContent') || 
                                     document.querySelector('.content') ||
                                     document.querySelector('#content');
                    return contentDiv ? contentDiv.innerText : document.body.innerText;
                }
            """)
            
            # Extract formulas from content
            formulas = extract_formulas(tab1_content)
            
            result = {
                "url": url,
                "tab1_content": tab1_content,
                "formulas": formulas,
                "status": "success"
            }
            
            return result
            
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "status": "failed"
            }
        finally:
            await browser.close()

def extract_formulas(content: str):
    """Extract formulas from tab1 content"""
    patterns = [
        # Salary calculation formulas
        (r'Tiền lương\s+(?:01|1)\s+tiết\s+dạy[^.]{20,300}', 'salary_per_lesson'),
        (r'Tiền lương[^=]{5,50}=\s*[^.]{20,200}', 'salary_calc'),
        
        # Mathematical operations with equals
        (r'[^.]{10,100}\s*=\s*[^.]{15,150}(?:[+\-×*/]\s*[^.]{5,100})*', 'equation'),
        
        # Teaching hours formulas
        (r'Số tiết[^=]{5,50}=\s*[^.]{20,200}', 'teaching_hours'),
        (r'Định mức[^=]{5,50}=\s*[^.]{15,150}', 'quota_calc'),
        
        # Amount definitions with numbers
        (r'(?:bằng|là)\s+[\d.,]+\s*(?:đồng|VNĐ|%)[^.]{0,100}', 'amount_definition'),
        
        # Multiplication formulas
        (r'[^.]{15,80}\s*[×x*]\s*[^.]{15,80}', 'multiplication'),
        
        # Percentage calculations
        (r'[\d.,]+\s*%[^.]{10,100}', 'percentage'),
        
        # Rate per unit
        (r'[\d.,]+\s*đồng/[^.]{5,50}', 'rate_per_unit'),
    ]
    
    formulas = []
    for pattern, formula_type in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            formula_text = match.group(0).strip()
            if len(formula_text) > 15:  # Filter out too short matches
                # Get context around the formula
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                
                formulas.append({
                    'formula': formula_text,
                    'type': formula_type,
                    'context': context,
                    'confidence': 0.8
                })
    
    return formulas

def format_output(data):
    """Format the output for better readability"""
    if data.get('status') == 'failed':
        print(f"Failed to crawl: {data.get('error')}")
        return
    
    print("\n" + "="*80)
    print("TAB1 CONTENT")
    print("="*80)
    
    content = data.get('tab1_content', '')
    if content:
        # Show first 1000 characters
        preview = content[:1000] + "..." if len(content) > 1000 else content
        print(preview)
    else:
        print("No content found")
    
    print("\n" + "="*80)
    print("EXTRACTED FORMULAS")
    print("="*80)
    
    formulas = data.get('formulas', [])
    if formulas:
        for i, formula in enumerate(formulas, 1):
            print(f"\n{i}. Type: {formula.get('type', 'unknown')}")
            print(f"   Formula: {formula.get('formula', '')}")
            print(f"   Confidence: {formula.get('confidence', 0):.2f}")
            if formula.get('context'):
                context = formula['context'][:200] + "..." if len(formula['context']) > 200 else formula['context']
                print(f"   Context: {context}")
    else:
        print("No formulas found")
    
    print("\n" + "="*80)

async def main():
    print("Starting tab1 crawler...")
    result = await crawl_tab1_content()
    
    # Save raw data
    os.makedirs('data', exist_ok=True)
    with open('data/tab1_content.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Raw data saved to: data/tab1_content.json")
    
    # Format and display
    format_output(result)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Quick script to crawl a single URL and format output nicely
"""

import asyncio
import json
from playwright.async_api import async_playwright
from tvpl_crawler.core.parser import TVPLParser
import os
import re

async def crawl_single_url(url: str):
    """Crawl a single URL and return formatted data"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Load cookies if available
        cookies_file = "data/cookies.json"
        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("✅ Loaded cookies from data/cookies.json")
            except:
                print("⚠️ Could not load cookies, continuing without login")
        
        page = await context.new_page()
        parser = TVPLParser()
        
        try:
            print(f"🔄 Crawling: {url}")
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Extract document info
            doc_info = await parser.extract_document_info(page)
            
            # Extract tab4 relations
            tab4_data = await parser.extract_tab4_relations(page)
            
            # Extract tab8 downloads
            tab8_data = await parser.extract_tab8_downloads(page)
            
            # Extract formulas from content
            formulas = await extract_formulas_from_page(page)
            
            result = {
                "url": url,
                "doc_info": doc_info,
                "tab4": tab4_data,
                "tab8": tab8_data,
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

async def extract_formulas_from_page(page):
    """Extract formulas from the main content"""
    try:
        # Get main content text
        content = await page.evaluate("""
            () => {
                const contentDiv = document.querySelector('#ctl00_Content_divContent') || 
                                 document.querySelector('.content') ||
                                 document.querySelector('#content');
                return contentDiv ? contentDiv.innerText : document.body.innerText;
            }
        """)
        
        # Enhanced formula patterns for Vietnamese legal documents
        
        patterns = [
            # Salary calculation formulas
            (r'Tiền lương\s+(?:01|1)\s+tiết\s+dạy[^=]{0,50}=\s*[^.]{20,300}', 'salary_per_lesson'),
            (r'Tiền lương[^=]{5,50}=\s*[^.]{20,200}', 'salary_calc'),
            
            # Mathematical operations with equals
            (r'[^.]{10,100}\s*=\s*[^.]{15,150}(?:[+\-×*/]\s*[^.]{5,100})*', 'equation'),
            
            # Teaching hours formulas
            (r'Số tiết[^=]{5,50}=\s*[^.]{20,200}', 'teaching_hours'),
            (r'Định mức tiết dạy[^=]{5,50}=\s*[^.]{20,200}', 'quota_calc'),
            
            # Rate calculations
            (r'Mức[^=]{5,50}=\s*[^.]{15,150}', 'rate_calc'),
            
            # Amount definitions
            (r'(?:bằng|là)\s+[\d.,]+\s*(?:đồng|VNĐ|%)[^.]{0,100}', 'amount_definition'),
        ]
        
        formulas = []
        for pattern, formula_type in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                formula_text = match.group(0).strip()
                if len(formula_text) > 20:  # Filter out too short matches
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
        
    except Exception as e:
        print(f"Error extracting formulas: {e}")
        return []

def format_output(data):
    """Format the output for better readability"""
    if data.get('status') == 'failed':
        print(f"❌ Failed to crawl: {data.get('error')}")
        return
    
    print("\n" + "="*80)
    print("📄 DOCUMENT INFORMATION")
    print("="*80)
    
    doc_info = data.get('doc_info', {})
    for key, value in doc_info.items():
        if value:
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n" + "="*80)
    print("🔗 DOCUMENT RELATIONS (TAB 4)")
    print("="*80)
    
    tab4 = data.get('tab4', {})
    relations = tab4.get('relations', {})
    
    if relations:
        for relation_type, docs in relations.items():
            if docs:
                print(f"\n{relation_type.replace('_', ' ').title()} ({len(docs)} documents):")
                for i, doc in enumerate(docs[:3], 1):  # Show first 3
                    print(f"  {i}. {doc.get('title', 'N/A')}")
                if len(docs) > 3:
                    print(f"  ... and {len(docs) - 3} more")
    else:
        print("No relations found")
    
    print(f"\nTotal relations: {tab4.get('total', 0)}")
    
    print("\n" + "="*80)
    print("📥 DOWNLOAD LINKS (TAB 8)")
    print("="*80)
    
    tab8 = data.get('tab8', {})
    links = tab8.get('links', [])
    
    if links:
        for i, link in enumerate(links, 1):
            print(f"{i}. {link.get('text', 'Download link')}")
            print(f"   URL: {link.get('url', 'N/A')}")
    else:
        print("No download links found")
    
    print("\n" + "="*80)
    print("🧮 EXTRACTED FORMULAS")
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
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("🚀 Starting crawler for education document...")
    result = await crawl_single_url(url)
    
    # Save raw data
    with open('data/single_url_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("💾 Raw data saved to: data/single_url_result.json")
    
    # Format and display
    format_output(result)

if __name__ == "__main__":
    asyncio.run(main())
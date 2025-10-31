#!/usr/bin/env python3
"""
Simple crawler for the education document
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright
import os

async def crawl_education_document():
    """Crawl the specific education document and extract data"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
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
                print("Loaded cookies")
            except:
                print("No cookies loaded")
        
        page = await context.new_page()
        
        try:
            print(f"Loading: {url}")
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            await page.wait_for_timeout(3000)  # Wait for dynamic content
            
            # Extract document info from the main table
            doc_info = await page.evaluate("""
                () => {
                    const info = {};
                    
                    // Find the main info table
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const rows = table.querySelectorAll('tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td, th');
                            if (cells.length === 2) {
                                const label = cells[0].innerText.trim().replace(':', '');
                                const value = cells[1].innerText.trim();
                                if (label && value) {
                                    info[label] = value;
                                }
                            }
                        }
                    }
                    
                    // Get title
                    const h1 = document.querySelector('h1');
                    if (h1) {
                        info['Tiêu đề'] = h1.innerText.trim();
                    }
                    
                    return info;
                }
            """)
            
            # Extract tab4 relations
            tab4_data = await page.evaluate("""
                () => {
                    const relations = {};
                    
                    // Click tab4 if exists
                    const tab4Link = document.querySelector('a[href="#tab4"]');
                    if (tab4Link) {
                        tab4Link.click();
                    }
                    
                    // Wait a bit for content to load
                    setTimeout(() => {}, 1000);
                    
                    const tab4Content = document.querySelector('#tab4');
                    if (tab4Content) {
                        const links = tab4Content.querySelectorAll('a[href*="/van-ban/"]');
                        const linkList = [];
                        links.forEach(link => {
                            linkList.push({
                                title: link.innerText.trim(),
                                url: link.href
                            });
                        });
                        relations['related_documents'] = linkList;
                    }
                    
                    return {
                        relations: relations,
                        total: Object.values(relations).flat().length
                    };
                }
            """)
            
            # Extract tab8 downloads
            tab8_data = await page.evaluate("""
                () => {
                    const downloads = [];
                    
                    // Click tab8 if exists
                    const tab8Link = document.querySelector('a[href="#tab8"]');
                    if (tab8Link) {
                        tab8Link.click();
                    }
                    
                    setTimeout(() => {}, 1000);
                    
                    const tab8Content = document.querySelector('#tab8');
                    if (tab8Content) {
                        const links = tab8Content.querySelectorAll('a[href]');
                        links.forEach(link => {
                            const href = link.href;
                            const text = link.innerText.trim();
                            if (href && text && (href.includes('.pdf') || href.includes('.doc') || href.includes('download'))) {
                                downloads.push({
                                    text: text,
                                    url: href
                                });
                            }
                        });
                    }
                    
                    return { links: downloads };
                }
            """)
            
            # Extract formulas from main content
            content_text = await page.evaluate("""
                () => {
                    const contentDiv = document.querySelector('#ctl00_Content_divContent') || 
                                     document.querySelector('.content') ||
                                     document.querySelector('#content') ||
                                     document.body;
                    return contentDiv ? contentDiv.innerText : '';
                }
            """)
            
            # Extract formulas using regex patterns
            formulas = extract_formulas(content_text)
            
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

def extract_formulas(content: str):
    """Extract formulas from content using enhanced patterns"""
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
        
        # Multiplication formulas
        (r'[^.]{15,80}\s*[×x*]\s*[^.]{15,80}', 'multiplication'),
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

def format_output(data):
    """Format the output for better readability"""
    if data.get('status') == 'failed':
        print(f"Failed to crawl: {data.get('error')}")
        return
    
    print("\n" + "="*80)
    print("DOCUMENT INFORMATION")
    print("="*80)
    
    doc_info = data.get('doc_info', {})
    for key, value in doc_info.items():
        if value:
            print(f"{key}: {value}")
    
    print("\n" + "="*80)
    print("DOCUMENT RELATIONS (TAB 4)")
    print("="*80)
    
    tab4 = data.get('tab4', {})
    relations = tab4.get('relations', {})
    
    if relations:
        for relation_type, docs in relations.items():
            if docs:
                print(f"\n{relation_type.replace('_', ' ').title()} ({len(docs)} văn bản):")
                for i, doc in enumerate(docs[:5], 1):  # Show first 5
                    print(f"  {i}. {doc.get('title', 'N/A')}")
                    print(f"     URL: {doc.get('url', 'N/A')}")
                if len(docs) > 5:
                    print(f"  ... and {len(docs) - 5} more documents")
    else:
        print("No document relations found")
    
    print(f"\nTotal relations: {tab4.get('total', 0)}")
    
    print("\n" + "="*80)
    print("DOWNLOAD LINKS (TAB 8)")
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
    print("CALCULATION FORMULAS")
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
        print("No calculation formulas found")
    
    print("\n" + "="*80)

async def main():
    print("Starting crawler for education document...")
    result = await crawl_education_document()
    
    # Save raw data
    os.makedirs('data', exist_ok=True)
    with open('data/education_document.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Raw data saved to: data/education_document.json")
    
    # Format and display
    format_output(result)

if __name__ == "__main__":
    asyncio.run(main())
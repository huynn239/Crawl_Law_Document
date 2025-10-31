#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crawl công thức tính toán từ tab1 (nội dung) - version đơn giản không cần crawl4ai"""
import json
import sys
import asyncio
import re
from pathlib import Path
from typing import Dict, List

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

def extract_formulas_regex_improved(html_content: str) -> List[Dict]:
    """Improved regex extraction for mathematical formulas"""
    formulas = []
    
    # Clean HTML first - remove tags but keep text
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Patterns cho các loại công thức thực sự - chính xác hơn
    patterns = [
        # Công thức có dấu = với số tiền cụ thể
        r'([A-Za-zÀ-ỹ\s]{5,50})\s*=\s*([\d.,]+(?:\s*(?:đồng|VNĐ|%))?)(?:\s*/\s*[A-Za-zÀ-ỹ]+)?',
        
        # Công thức tính % rõ ràng
        r'([\d.,]+)\s*%\s*(?:của|×|\*)\s*([\d.,]+(?:\s*(?:đồng|VNĐ))?)',
        
        # Công thức có phép tính + - × /
        r'([A-Za-zÀ-ỹ\s]{5,40})\s*=\s*([\d.,]+)\s*([+\-×*/])\s*([\d.,]+)(?:\s*(?:đồng|VNĐ|%))?',
        
        # Mức/Tỷ lệ với số cụ thể
        r'((?:mức|tỷ\s*lệ)\s*[^:]{5,40}):\s*([\d.,]+\s*(?:%|đồng|VNĐ))',
        
        # Công thức tính lương/phụ cấp
        r'((?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí)\s*[^=]{5,40})\s*=\s*([\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))?)',
        
        # Công thức có từ "tính" hoặc "bằng"
        r'(tính|bằng)\s*([^.]{10,80}(?:[\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))))',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            formula_text = match.group(0).strip()
            
            # Filter out HTML artifacts and invalid formulas
            if (len(formula_text) > 15 and len(formula_text) < 300 and
                not any(x in formula_text.lower() for x in ['<', '>', 'href', 'class', 'style', 'div', 'span', 'aspx', 'listidlaw', 'javascript', 'function', 'var ', 'document']) and
                any(char.isdigit() for char in formula_text) and
                ('=' in formula_text or '%' in formula_text or any(op in formula_text for op in ['+', '-', '×', '*', '/'])) and
                any(word in formula_text.lower() for word in ['lương', 'phụ cấp', 'thuế', 'phí', 'tiền', 'mức', 'tỷ lệ', 'tính', 'bằng', 'đồng', 'vnd', '%'])):
                
                formulas.append({
                    "name": f"Công thức {len(formulas) + 1}",
                    "formula": formula_text,
                    "description": f"Công thức tính toán (pattern {i})",
                    "context": formula_text[:150] + "..." if len(formula_text) > 150 else formula_text
                })
    
    # Remove duplicates
    seen = set()
    unique_formulas = []
    for f in formulas:
        if f['formula'] not in seen:
            seen.add(f['formula'])
            unique_formulas.append(f)
    
    return unique_formulas[:20]  # Limit to top 20 formulas

async def extract_tab1_content_simple(page, url: str) -> Dict:
    """Extract tab1 content đơn giản với regex patterns cải thiện"""
    try:
        # Click tab nội dung với nhiều selector
        clicked = False
        selectors = ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')", "#tab1"]
        
        for selector in selectors:
            try:
                await page.click(selector, timeout=2000)
                clicked = True
                break
            except:
                continue
        
        if not clicked:
            # Fallback: navigate directly to tab1
            await page.evaluate("() => { location.hash = '#tab1'; }")
        
        await page.wait_for_timeout(3000)  # Đợi lâu hơn cho content load
        
        # Get tab1 content
        tab1_content = ""
        try:
            tab1_element = await page.query_selector("#tab1")
            if tab1_element:
                tab1_content = await tab1_element.inner_html()
        except:
            pass
        
        # Extract formulas using improved regex
        formulas = extract_formulas_regex_improved(tab1_content)
        
        return {
            "url": url,
            "tab1_content_length": len(tab1_content),
            "formulas": formulas,
            "total_formulas": len(formulas),
            "extraction_method": "regex_improved"
        }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "formulas": [],
            "total_formulas": 0
        }

async def crawl_formulas():
    """Main crawl function"""
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Load cookies
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        
        for idx, item in enumerate(links, 1):
            url = item.get("Url") or item.get("url", "")
            title = item.get("Tên văn bản") or item.get("title", "")
            
            print(f"[{idx}/{len(links)}] {title[:50]}...")
            
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                
                result = await extract_tab1_content_simple(page, url)
                result["stt"] = idx
                result["title"] = title
                results.append(result)
                
                formulas_count = result.get("total_formulas", 0)
                print(f"  ✓ Found {formulas_count} formulas")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    "stt": idx,
                    "url": url,
                    "title": title,
                    "error": str(e),
                    "formulas": [],
                    "total_formulas": 0
                })
            finally:
                await page.close()
        
        await browser.close()
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawl_formulas_simple.py <input_file> [output_file]")
        print("Example: python crawl_formulas_simple.py data/links.json data/formulas.json")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_formulas.json"

    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"Extracting formulas from {len(links)} documents using improved regex patterns")

    # Run crawler
    results = asyncio.run(crawl_formulas())

    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    total_formulas = sum(r.get("total_formulas", 0) for r in results)
    successful = len([r for r in results if not r.get("error")])
    failed = len(results) - successful

    print(f"\n{'='*60}")
    print(f"Formula extraction complete!")
    print(f"Documents: {len(results)} ({successful} success, {failed} failed)")
    print(f"Total formulas found: {total_formulas}")
    print(f"Output: {output_file}")
    print(f"{'='*60}")

    # Show sample formulas
    sample_formulas = []
    for result in results:
        sample_formulas.extend(result.get("formulas", [])[:2])
        if len(sample_formulas) >= 5:
            break

    if sample_formulas:
        print(f"\nSample formulas:")
        for i, formula in enumerate(sample_formulas[:5], 1):
            name = formula.get("name", "N/A")
            formula_text = formula.get("formula", "")[:80]
            print(f"  {i}. {name}: {formula_text}...")
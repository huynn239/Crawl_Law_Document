#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crawl nhanh các công thức tính toán từ tab1 (nội dung) của văn bản pháp luật"""
import json
import sys
import asyncio
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from tvpl_crawler.formula_extractor import extract_tab1_content_simple, extract_formulas_with_crawl4ai
from playwright.async_api import async_playwright

if len(sys.argv) < 2:
    print("Usage: python crawl_formulas_fast.py <input_file> [output_file] [method]")
    print("Example: python crawl_formulas_fast.py data/links.json data/formulas.json hybrid")
    print("Methods: hybrid (crawl4ai+ultimate), playwright (default), crawl4ai")
    sys.exit(1)

input_file = Path(sys.argv[1])
output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_formulas.json"
method = sys.argv[3] if len(sys.argv) >= 4 else "hybrid"

# Load links
links = json.loads(input_file.read_text(encoding="utf-8"))
print(f"Extracting formulas from {len(links)} documents using {method}")

async def crawl_formulas():
    results = []
    
    if method == "crawl4ai" or method == "hybrid":
        # Sử dụng Crawl4AI + LLM
        from tvpl_crawler.formula_extractor import extract_formulas_with_crawl4ai
        
        for idx, item in enumerate(links, 1):
            url = item.get("Url") or item.get("url", "")
            title = item.get("Ten van ban") or item.get("title", "")
            
            print(f"[{idx}/{len(links)}] {title[:50]}...")
            
            try:
                # Thử Crawl4AI trước
                result = await extract_formulas_with_crawl4ai(url, "data/cookies.json")
                
                # Nếu Crawl4AI không tìm được gì, dùng ultimate hybrid extractor
                if result.get("total_formulas", 0) == 0:
                    print("  Crawl4AI found nothing, trying ultimate hybrid extractor...")
                    try:
                        from ultimate_formula_extractor import UltimateFormulaExtractor
                        import os
                        from dotenv import load_dotenv
                        
                        load_dotenv()
                        openai_key = os.getenv('OPENAI_API_KEY')
                        extractor = UltimateFormulaExtractor(openai_api_key=openai_key)
                        
                        backup_result = await extractor.extract_formulas(url=url)
                        
                        if backup_result.get("total_formulas", 0) > 0:
                            result = backup_result
                            result["extraction_method"] = "ultimate_hybrid_backup"
                            print(f"  Ultimate extractor found {result['total_formulas']} formulas")
                    except Exception as e:
                        print(f"  Ultimate extractor failed: {e}")
                
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
    
    else:
        # Sử dụng Playwright + Regex
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
                title = item.get("Ten van ban") or item.get("title", "")
                
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
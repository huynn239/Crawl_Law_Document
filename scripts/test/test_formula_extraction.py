#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script để thử nghiệm extract công thức từ tab1"""
import asyncio
import json
from pathlib import Path
from tvpl_crawler.extractors.formula_extractor import extract_formulas_with_crawl4ai, extract_tab1_content_simple
from playwright.async_api import async_playwright

async def test_formula_extraction():
    """Test extract công thức từ một văn bản mẫu"""
    
    # URL test - chọn văn bản có nhiều công thức tính toán
    test_url = "https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Nghi-dinh-123-2020-ND-CP-huong-dan-Luat-Quan-ly-thue-449894.aspx"
    cookies_path = "data/cookies.json"
    
    print(f"🧪 Testing formula extraction from: {test_url}")
    
    # Method 1: Crawl4AI với LLM (nếu có)
    try:
        print("\n📊 Method 1: Crawl4AI + LLM")
        result_crawl4ai = await extract_formulas_with_crawl4ai(test_url, cookies_path)
        print(f"✓ Found {result_crawl4ai.get('total_formulas', 0)} formulas")
        for i, formula in enumerate(result_crawl4ai.get('formulas', [])[:3], 1):
            print(f"  {i}. {formula.get('name', 'N/A')}: {formula.get('formula', '')[:100]}...")
    except Exception as e:
        print(f"✗ Crawl4AI failed: {e}")
        result_crawl4ai = None
    
    # Method 2: Playwright + Regex fallback
    print("\n🎭 Method 2: Playwright + Regex")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Load cookies
        context_options = {}
        if Path(cookies_path).exists():
            context_options["storage_state"] = cookies_path
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            result_playwright = await extract_tab1_content_simple(page, test_url)
            print(f"✓ Found {result_playwright.get('total_formulas', 0)} formulas")
            for i, formula in enumerate(result_playwright.get('formulas', [])[:3], 1):
                print(f"  {i}. {formula.get('name', 'N/A')}: {formula.get('formula', '')[:100]}...")
        except Exception as e:
            print(f"✗ Playwright failed: {e}")
            result_playwright = {"error": str(e)}
        
        await browser.close()
    
    # Save results
    results = {
        "test_url": test_url,
        "crawl4ai_result": result_crawl4ai,
        "playwright_result": result_playwright,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    output_file = Path("data/formula_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n🎯 Summary:")
    if result_crawl4ai:
        print(f"  - Crawl4AI: {result_crawl4ai.get('total_formulas', 0)} formulas")
    if result_playwright:
        print(f"  - Playwright: {result_playwright.get('total_formulas', 0)} formulas")

if __name__ == "__main__":
    asyncio.run(test_formula_extraction())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test LLM extraction với OpenAI API"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Set OpenAI API key (thay YOUR_API_KEY bằng key thực)
# os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"

from tvpl_crawler.extractors.formula_extractor import extract_formulas_with_crawl4ai

async def test_llm_extraction():
    """Test LLM extraction với URL thực"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("Testing LLM extraction with Crawl4AI...")
    print(f"URL: {url}")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set. Please set it first:")
        print("   set OPENAI_API_KEY=your_api_key_here")
        print("   or edit this script to set os.environ['OPENAI_API_KEY']")
        return
    
    print(f"✓ OpenAI API key found: {api_key[:10]}...")
    
    try:
        result = await extract_formulas_with_crawl4ai(url, "data/cookies.json")
        
        print(f"\n{'='*60}")
        print(f"LLM Extraction Results:")
        print(f"URL: {result['url']}")
        print(f"Content length: {result.get('tab1_content_length', 0)}")
        print(f"Total formulas: {result.get('total_formulas', 0)}")
        print(f"Method: {result.get('extraction_method', 'unknown')}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        formulas = result.get('formulas', [])
        if formulas:
            print(f"\nFormulas found:")
            for i, formula in enumerate(formulas, 1):
                name = formula.get('name', 'N/A')
                formula_text = formula.get('formula', '')
                description = formula.get('description', '')
                print(f"  {i}. {name}")
                print(f"     Formula: {formula_text}")
                print(f"     Description: {description}")
                print()
        else:
            print("No formulas found.")
        
        # Save results
        output_file = Path("data/test_llm_extraction.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"✗ Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_extraction())
#!/usr/bin/env python3
"""Test adaptive extractor with real document"""

import asyncio
import json
import os
from dotenv import load_dotenv
from scripts.extract.adaptive_formula_extractor import AdaptiveFormulaExtractor

async def test_real_document():
    load_dotenv()
    
    # Initialize extractor
    openai_key = os.getenv('OPENAI_API_KEY')
    extractor = AdaptiveFormulaExtractor(openai_api_key=openai_key)
    
    # URL văn bản thực
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("Crawling document from URL...")
    result = await extractor.extract_formulas(url=url)
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/adaptive_real_document.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Crawl completed!")
    print(f"Detected domain: {result['detected_domain']}")
    print(f"Found: {result['total_formulas']} formulas, {result['total_parameters']} parameters")
    print(f"Method: {result['extraction_method']}")
    print(f"Content length: {result['content_length']} characters")
    print(f"Results saved to: {output_file}")
    
    # Show top 5 formulas
    print(f"\nTop 5 formulas found:")
    for i, formula in enumerate(result['formulas'][:5], 1):
        name = formula['name'][:80] + "..." if len(formula['name']) > 80 else formula['name']
        print(f"{i}. {name}")
        print(f"   Type: {formula['type']} | Confidence: {formula['confidence']:.2f}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_real_document())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test crawl4ai với regex patterns đã cải thiện"""
import asyncio
import sys
import re
from typing import Dict, List

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from crawl4ai import AsyncWebCrawler

def extract_formulas_from_text(text: str) -> List[Dict]:
    """Extract formulas using improved regex patterns"""
    formulas = []
    
    # Clean text
    clean_text = re.sub(r'\s+', ' ', text).strip()
    
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
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            formula_text = match.group(0).strip()
            
            # Filter out invalid formulas
            if (len(formula_text) > 15 and len(formula_text) < 300 and
                any(char.isdigit() for char in formula_text) and
                ('=' in formula_text or '%' in formula_text or any(op in formula_text for op in ['+', '-', '×', '*', '/'])) and
                any(word in formula_text.lower() for word in ['lương', 'phụ cấp', 'thuế', 'phí', 'tiền', 'mức', 'tỷ lệ', 'đồng', 'vnd', '%'])):
                
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
    
    return unique_formulas[:20]

async def test_crawl4ai_extraction():
    """Test crawl4ai với URL thực"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            bypass_cache=True,
            js_code="""
            // Click tab nội dung (tab1)
            const tab1 = document.querySelector('#aNoiDung') || document.querySelector('a[href="#tab1"]');
            if (tab1) {
                tab1.click();
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
            
            // Đợi nội dung load
            await new Promise(resolve => setTimeout(resolve, 3000));
            """,
            wait_for="networkidle"
        )
        
        if result.success:
            print(f"✓ Crawled successfully")
            print(f"Content length: {len(result.cleaned_html)}")
            
            # Extract formulas using regex
            formulas = extract_formulas_from_text(result.cleaned_html)
            
            print(f"Found {len(formulas)} formulas:")
            for i, formula in enumerate(formulas, 1):
                print(f"  {i}. {formula['name']}: {formula['formula']}")
            
            return {
                "url": url,
                "content_length": len(result.cleaned_html),
                "formulas": formulas,
                "total_formulas": len(formulas),
                "extraction_method": "crawl4ai_regex"
            }
        else:
            print(f"✗ Failed: {result.error_message}")
            return {
                "url": url,
                "error": result.error_message,
                "formulas": [],
                "total_formulas": 0
            }

if __name__ == "__main__":
    print("Testing Crawl4AI with improved regex patterns...")
    result = asyncio.run(test_crawl4ai_extraction())
    
    print(f"\n{'='*60}")
    print(f"Crawl4AI test complete!")
    print(f"Total formulas found: {result.get('total_formulas', 0)}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"{'='*60}")
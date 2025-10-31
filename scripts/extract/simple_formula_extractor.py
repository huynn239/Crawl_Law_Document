#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple Formula Extractor - Đơn giản và hiệu quả"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class SimpleFormulaExtractor:
    def __init__(self):
        # Patterns đơn giản và hiệu quả
        self.patterns = [
            # 1. Mức ... = số đồng
            (r'(mức\s+[^=:]{5,50})\s*[=:]\s*([\d.,]+\s*đồng(?:/(?:tháng|năm))?)', 0.9, 'amount'),
            
            # 2. Tỷ lệ ... : số%
            (r'(tỷ\s*lệ\s+[^:=]{5,40})\s*[=:]\s*([\d.,]+\s*%)', 0.9, 'rate'),
            
            # 3. Lệ phí ... : số đồng
            (r'(lệ\s*phí\s+[^:]{5,50})\s*:\s*([\d.,]+\s*đồng)', 0.85, 'fee'),
            
            # 4. Từ số đến số đồng
            (r'từ\s*([\d.,]+)\s*đến\s*([\d.,]+)\s*(đồng)', 0.8, 'range'),
            
            # 5. Công thức có dấu =
            (r'([^=]{10,50})\s*=\s*([^.]{10,60}[×*]\s*[^.]{5,40})', 0.75, 'formula'),
        ]
        
        # Từ khóa loại trừ
        self.exclude = [
            r'\d+/\d+/[A-Z-]+',  # Số văn bản
            r'điều\s*\d+', r'khoản\s*\d+', r'mục\s*\d+',  # Điều khoản
            r'\d{1,2}/\d{1,2}/\d{4}',  # Ngày tháng
            r'trang\s*\d+', r'phụ\s*lục\s*\d+',  # Số trang
        ]
    
    def is_valid(self, text: str) -> bool:
        """Kiểm tra đơn giản"""
        # Loại bỏ patterns không hợp lệ
        for pattern in self.exclude:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Phải có số và từ khóa quan trọng
        has_number = re.search(r'\d', text)
        has_keyword = any(word in text.lower() for word in 
                         ['mức', 'tỷ lệ', 'lệ phí', 'thuế', 'lương', 'phí', 'phạt'])
        
        return has_number and has_keyword and 10 <= len(text) <= 150
    
    def extract_formulas(self, text: str) -> List[Dict]:
        """Trích xuất đơn giản"""
        if not text:
            return []
        
        results = []
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        for pattern, confidence, formula_type in self.patterns:
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                if self.is_valid(formula_text):
                    # Tạo tên từ group đầu tiên hoặc từ formula
                    if match.groups() and match.group(1):
                        name = match.group(1).strip()
                    else:
                        name = formula_text[:30] + "..."
                    
                    results.append({
                        'name': name,
                        'formula': formula_text,
                        'confidence': confidence,
                        'type': formula_type
                    })
        
        # Loại bỏ trùng lặp
        seen = set()
        unique = []
        for r in results:
            key = r['formula'].lower()
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        return sorted(unique, key=lambda x: x['confidence'], reverse=True)[:5]
    
    async def extract_from_page(self, page, url: str) -> Dict:
        """Trích xuất từ trang web"""
        try:
            # Click tab nội dung
            for selector in ["#aNoiDung", "a[href='#tab1']"]:
                try:
                    await page.click(selector, timeout=2000)
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy nội dung
            content = ""
            try:
                element = await page.query_selector("#tab1")
                if element:
                    content = await element.inner_text()
                else:
                    content = await page.inner_text("body")
            except:
                content = await page.inner_text("body")
            
            formulas = self.extract_formulas(content)
            
            return {
                'url': url,
                'content_length': len(content),
                'formulas': formulas,
                'total_formulas': len(formulas),
                'extraction_method': 'simple'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

# Test function
def test_simple_extractor():
    """Test với nội dung mẫu"""
    extractor = SimpleFormulaExtractor()
    
    test_cases = [
        "Mức lương cơ bản: 1.800.000 đồng/tháng",
        "Tỷ lệ thuế thu nhập cá nhân: 10%", 
        "Lệ phí cấp giấy phép lái xe: 135.000 đồng",
        "Từ 500.000 đến 1.000.000 đồng",
        "Thuế = Thu nhập × 15%",
        "Thông tư số 156/2011/TT-BTC",  # Should reject
    ]
    
    print("TEST SIMPLE EXTRACTOR")
    print("=" * 30)
    
    success = 0
    for i, test in enumerate(test_cases, 1):
        formulas = extractor.extract_formulas(test)
        if formulas:
            success += 1
            print(f"{i}. ✓ {test}")
            print(f"   -> {formulas[0]['name']} ({formulas[0]['type']})")
        else:
            print(f"{i}. ✗ {test}")
    
    print(f"\nSuccess: {success}/{len(test_cases)} ({success/len(test_cases)*100:.1f}%)")
    return success >= 4

async def main():
    """Main function for CLI usage"""
    if len(sys.argv) < 2:
        test_simple_extractor()
        return
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_simple.json"
    
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"Simple Formula Extraction - Processing {len(links)} documents")
    
    extractor = SimpleFormulaExtractor()
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        
        for idx, item in enumerate(links, 1):
            url = item.get("Url") or item.get("url", "")
            title = item.get("Tên văn bản") or item.get("title", "")
            
            print(f"[{idx}/{len(links)}] Processing...")
            
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                
                result = await extractor.extract_from_page(page, url)
                result["stt"] = idx
                result["title"] = title
                results.append(result)
                
                if result.get("total_formulas", 0) > 0:
                    print(f"  ✓ Found {result['total_formulas']} formulas")
                else:
                    print(f"  ✗ No formulas")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    "stt": idx, "url": url, "title": title,
                    "error": str(e), "formulas": [], "total_formulas": 0
                })
            finally:
                await page.close()
        
        await browser.close()
    
    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    total = sum(r.get("total_formulas", 0) for r in results)
    success = len([r for r in results if r.get("total_formulas", 0) > 0])
    
    print(f"\nSUMMARY: {success}/{len(results)} docs, {total} formulas total")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        asyncio.run(main())
    else:
        test_simple_extractor()
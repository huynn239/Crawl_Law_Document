#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ultra Formula Extractor - Phiên bản siêu cải tiến với độ chính xác cao"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class UltraFormulaExtractor:
    def __init__(self):
        # Patterns siêu chính xác - chỉ lấy công thức thực sự
        self.patterns = [
            # 1. Mức tiền với từ khóa mạnh
            {
                'pattern': r'(mức\s+(?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí|lệ\s*phí|giảm\s*trừ)[^=:]{0,40})\s*[=:]\s*([\d.,]+)\s*(đồng(?:/(?:tháng|năm|ngày))?)',
                'confidence': 0.95,
                'type': 'salary_amount'
            },
            
            # 2. Tỷ lệ phần trăm với từ khóa mạnh
            {
                'pattern': r'(tỷ\s*lệ\s+(?:thuế|phí|bảo\s*hiểm|đóng\s*góp|phụ\s*cấp)[^:=]{0,40})\s*[=:]\s*([\d.,]+\s*%)',
                'confidence': 0.95,
                'type': 'tax_rate'
            },
            
            # 3. Công thức tính với dấu =
            {
                'pattern': r'((?:thuế|lương|phụ\s*cấp|bảo\s*hiểm)[^=]{5,50})\s*=\s*([^.]{10,80}(?:×|x|\*)[^.]{5,50})',
                'confidence': 0.9,
                'type': 'calculation'
            },
            
            # 4. Khoảng tiền với từ khóa
            {
                'pattern': r'((?:mức\s*)?(?:phạt|lương|phí|thuế)[^từ]{0,30})\s*từ\s*([\d.,]+)\s*đến\s*([\d.,]+)\s*(đồng|triệu|tỷ)',
                'confidence': 0.85,
                'type': 'money_range'
            },
            
            # 5. Lệ phí cụ thể
            {
                'pattern': r'(lệ\s*phí\s+(?:cấp|gia\s*hạn|đổi)[^:]{5,50})\s*:\s*([\d.,]+)\s*(đồng)',
                'confidence': 0.9,
                'type': 'fee'
            }
        ]
        
        # Từ khóa bắt buộc phải có
        self.required_keywords = [
            'mức', 'tỷ lệ', 'thuế', 'phí', 'lương', 'phụ cấp', 'bảo hiểm',
            'giảm trừ', 'phạt', 'trợ cấp', 'lệ phí', 'đóng góp'
        ]
        
        # Từ khóa loại trừ mạnh
        self.exclude_patterns = [
            r'\d+/\d+/[A-Z-]+',  # Số văn bản
            r'điều\s*\d+',       # Điều luật
            r'khoản\s*\d+',      # Khoản
            r'mục\s*\d+',        # Mục
            r'phụ\s*lục\s*\d+',  # Phụ lục
            r'\d{1,2}/\d{1,2}/\d{4}',  # Ngày tháng
            r'trang\s*\d+',      # Số trang
            r'số\s*\d+\s*ngày',  # Số ... ngày
        ]
    
    def is_valid_formula(self, text: str) -> bool:
        """Kiểm tra siêu nghiêm ngặt"""
        text_lower = text.lower()
        
        # Loại bỏ các pattern không hợp lệ
        for pattern in self.exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Phải có ít nhất một từ khóa bắt buộc
        has_required = any(keyword in text_lower for keyword in self.required_keywords)
        if not has_required:
            return False
        
        # Phải có số và đơn vị hoặc toán tử
        has_number = re.search(r'\d', text)
        has_unit = any(unit in text_lower for unit in ['đồng', '%', 'triệu', 'tỷ'])
        has_operator = any(op in text for op in ['=', '×', '*', '+', '-'])
        
        return has_number and (has_unit or has_operator)
    
    def extract_formulas(self, text: str) -> List[Dict]:
        """Trích xuất siêu chính xác"""
        if not text or len(text) < 50:
            return []
        
        results = []
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        for pattern_info in self.patterns:
            matches = re.finditer(pattern_info['pattern'], clean_text, re.IGNORECASE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                if self.is_valid_formula(formula_text) and len(formula_text) > 15:
                    # Tạo tên từ group đầu tiên
                    name = match.group(1).strip() if match.groups() else "Công thức"
                    
                    # Lấy context
                    start, end = match.span()
                    context_start = max(0, start - 100)
                    context_end = min(len(clean_text), end + 100)
                    context = clean_text[context_start:context_end]
                    
                    results.append({
                        'name': name[:60],
                        'formula': formula_text,
                        'description': f"{pattern_info['type']} - độ tin cậy {pattern_info['confidence']}",
                        'context': context,
                        'confidence': pattern_info['confidence'],
                        'type': pattern_info['type']
                    })
        
        # Loại bỏ trùng lặp
        seen = set()
        unique_results = []
        for result in results:
            key = result['formula'].lower().strip()
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return sorted(unique_results, key=lambda x: x['confidence'], reverse=True)[:10]
    
    async def extract_from_page(self, page, url: str) -> Dict:
        """Trích xuất từ trang web"""
        try:
            # Click tab nội dung
            for selector in ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')"]:
                try:
                    await page.click(selector, timeout=2000)
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy nội dung từ nhiều nguồn
            content = ""
            for selector in ["#tab1", ".tab-content", "body"]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if len(text) > len(content):
                            content = text
                except:
                    continue
            
            formulas = self.extract_formulas(content)
            
            return {
                'url': url,
                'content_length': len(content),
                'formulas': formulas,
                'total_formulas': len(formulas),
                'extraction_method': 'ultra_precise'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

async def main():
    if len(sys.argv) < 2:
        print("Usage: python ultra_formula_extractor.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_ultra.json"
    
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"Ultra Formula Extraction - Processing {len(links)} documents")
    
    extractor = UltraFormulaExtractor()
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
            
            print(f"[{idx}/{len(links)}] {title[:50]}...")
            
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
                    for formula in result["formulas"][:2]:
                        print(f"    - [{formula['confidence']:.2f}] {formula['name']}")
                else:
                    print(f"  ✗ No formulas found")
                
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
    
    # Summary
    total_formulas = sum(r.get("total_formulas", 0) for r in results)
    successful = len([r for r in results if r.get("total_formulas", 0) > 0])
    
    print(f"\n{'='*60}")
    print(f"ULTRA FORMULA EXTRACTION COMPLETE")
    print(f"Documents: {len(results)} | Success: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Total formulas: {total_formulas} | Avg: {total_formulas/len(results):.1f}")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
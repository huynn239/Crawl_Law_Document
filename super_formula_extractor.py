#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super Formula Extractor - Dựa trên nội dung thực đã đọc"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class SuperFormulaExtractor:
    def __init__(self):
        # Patterns siêu mạnh dựa trên nội dung thực
        self.patterns = [
            # 1. Công thức có dấu = rõ ràng
            {
                'pattern': r'([^.]{10,80})\s*=\s*([^.]{10,120})',
                'confidence': 0.9,
                'type': 'equation'
            },
            
            # 2. Công thức có × (nhân)
            {
                'pattern': r'([^.]{10,60})\s*×\s*([^.]{5,40})',
                'confidence': 0.85,
                'type': 'multiplication'
            },
            
            # 3. Không quá + số
            {
                'pattern': r'(không\s*quá)\s*([\d.,]+)\s*(tiết|đồng|%)',
                'confidence': 0.8,
                'type': 'limit'
            },
            
            # 4. Tỷ lệ phần trăm
            {
                'pattern': r'([\d.,]+)\s*%',
                'confidence': 0.7,
                'type': 'percentage'
            },
            
            # 5. Công thức phân số (có /)
            {
                'pattern': r'([^/]{10,60})\s*/\s*([^.]{5,60})',
                'confidence': 0.75,
                'type': 'division'
            },
            
            # 6. Tổng số + công thức
            {
                'pattern': r'(tổng\s*số[^=]{10,60})\s*=\s*([^.]{10,100})',
                'confidence': 0.8,
                'type': 'total_formula'
            }
        ]
        
        # Từ khóa bắt buộc
        self.required_keywords = [
            'tiền', 'lương', 'tiết', 'tổng', 'mức', 'tỷ lệ', 'định mức', 
            'không quá', 'bằng', 'tính', 'được', 'theo'
        ]
        
        # Loại trừ
        self.exclude = [
            r'\d+/\d+/[A-Z-]+',  # Số văn bản
            r'điều\s*\d+', r'khoản\s*\d+',  # Điều khoản
            r'\d{1,2}/\d{1,2}/\d{4}',  # Ngày tháng
            r'trang\s*\d+', r'mục\s*\d+',  # Số trang
        ]
    
    def is_valid_formula(self, text: str) -> bool:
        """Kiểm tra siêu nghiêm ngặt"""
        text_lower = text.lower()
        
        # Loại trừ
        for pattern in self.exclude:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Phải có từ khóa bắt buộc
        has_keyword = any(keyword in text_lower for keyword in self.required_keywords)
        
        # Phải có số hoặc toán tử
        has_number = re.search(r'\d', text)
        has_operator = any(op in text for op in ['=', '×', '*', '/', '+', '-', '%'])
        
        # Độ dài hợp lý
        length_ok = 15 <= len(text) <= 200
        
        return has_keyword and (has_number or has_operator) and length_ok
    
    def extract_formulas(self, text: str) -> List[Dict]:
        """Trích xuất siêu mạnh"""
        if not text:
            return []
        
        results = []
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        for pattern_info in self.patterns:
            pattern = pattern_info['pattern']
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                if self.is_valid_formula(formula_text):
                    # Tạo tên từ match
                    if match.groups() and match.group(1):
                        name = match.group(1).strip()[:50]
                    else:
                        name = formula_text[:30] + "..."
                    
                    # Context
                    start, end = match.span()
                    context_start = max(0, start - 100)
                    context_end = min(len(clean_text), end + 100)
                    context = clean_text[context_start:context_end]
                    
                    results.append({
                        'name': name,
                        'formula': formula_text,
                        'description': f"{pattern_info['type']} - confidence {pattern_info['confidence']}",
                        'context': context,
                        'confidence': pattern_info['confidence'],
                        'type': pattern_info['type']
                    })
        
        # Loại bỏ trùng lặp và sắp xếp
        seen = set()
        unique = []
        for r in results:
            key = r['formula'].lower().strip()
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique.append(r)
        
        return sorted(unique, key=lambda x: x['confidence'], reverse=True)[:10]
    
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
                'extraction_method': 'super_patterns'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

async def main():
    """Test với link lương giáo viên"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    extractor = SuperFormulaExtractor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            print("🚀 SUPER FORMULA EXTRACTION")
            print("=" * 50)
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            result = await extractor.extract_from_page(page, url)
            
            print(f"📄 Content length: {result.get('content_length', 0)}")
            print(f"🔍 Formulas found: {result.get('total_formulas', 0)}")
            
            if result.get('formulas'):
                print(f"\n✅ FOUND {len(result['formulas'])} FORMULAS:")
                
                for i, formula in enumerate(result['formulas'], 1):
                    print(f"\n{i}. [{formula['confidence']:.2f}] {formula['name']}")
                    print(f"   Formula: {formula['formula']}")
                    print(f"   Type: {formula['type']}")
                    print(f"   Context: {formula['context'][:80]}...")
                
                # Lưu kết quả
                output_file = Path("data/super_formulas.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n💾 Saved to: {output_file}")
            else:
                print("❌ No formulas found")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
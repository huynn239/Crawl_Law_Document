#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Simple Extractor - Cải tiến để nhận diện công thức lương"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class EnhancedSimpleExtractor:
    def __init__(self):
        # Patterns mở rộng cho lương giáo viên
        self.patterns = [
            # 1. Mức ... = số đồng
            (r'(mức\s+[^=:]{5,60})\s*[=:]\s*([\d.,]+\s*đồng(?:/(?:tháng|năm|tiết))?)', 0.9, 'salary_amount'),
            
            # 2. Tỷ lệ/Định mức ... : số%
            (r'((?:tỷ\s*lệ|định\s*mức)\s+[^:=]{5,50})\s*[=:]\s*([\d.,]+\s*(?:%|tiết|giờ))', 0.9, 'rate_quota'),
            
            # 3. Tiền lương ... bao gồm
            (r'(tiền\s*lương[^:]{10,80})\s*bao\s*gồm\s*:\s*([^.]{20,100})', 0.85, 'salary_components'),
            
            # 4. Không quá ... tiết/giờ
            (r'(không\s*quá)\s*([\d.,]+)\s*(tiết|giờ|đồng)', 0.8, 'limit'),
            
            # 5. Tổng số ... được tính
            (r'(tổng\s*số[^được]{10,60})\s*được\s*tính[^:]{0,20}:\s*([^.]{10,80})', 0.8, 'calculation_rule'),
            
            # 6. Căn cứ tính ... 
            (r'(căn\s*cứ\s*tính[^:]{10,60})\s*:\s*([^.]{10,100})', 0.75, 'calculation_basis'),
            
            # 7. Quy đổi ... ra tiết
            (r'(quy\s*đổi[^ra]{10,40})\s*ra\s*([\d.,]+\s*tiết)', 0.75, 'conversion'),
        ]
        
        # Từ khóa loại trừ
        self.exclude = [
            r'\d+/\d+/[A-Z-]+',  # Số văn bản
            r'điều\s*\d+', r'khoản\s*\d+', r'mục\s*\d+',  # Điều khoản
            r'\d{1,2}/\d{1,2}/\d{4}',  # Ngày tháng
            r'trang\s*\d+', r'phụ\s*lục\s*\d+',  # Số trang
            r'số\s*\d+\s*ngày',  # Số ... ngày
        ]
    
    def is_valid(self, text: str) -> bool:
        """Kiểm tra mở rộng cho lương"""
        # Loại bỏ patterns không hợp lệ
        for pattern in self.exclude:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Phải có từ khóa lương hoặc số
        has_salary_keyword = any(word in text.lower() for word in 
                               ['lương', 'tiền', 'mức', 'tỷ lệ', 'định mức', 'tiết', 'giờ', 'phụ cấp'])
        has_number = re.search(r'\d', text)
        
        return has_salary_keyword and has_number and 15 <= len(text) <= 300
    
    def extract_formulas(self, text: str) -> List[Dict]:
        """Trích xuất mở rộng"""
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
                    # Tạo tên từ group đầu tiên
                    if match.groups() and match.group(1):
                        name = match.group(1).strip()
                    else:
                        name = formula_text[:40] + "..."
                    
                    # Context
                    start, end = match.span()
                    context_start = max(0, start - 100)
                    context_end = min(len(clean_text), end + 100)
                    context = clean_text[context_start:context_end]
                    
                    results.append({
                        'name': name[:60],
                        'formula': formula_text,
                        'description': f"{formula_type} - {confidence}",
                        'context': context,
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
        
        return sorted(unique, key=lambda x: x['confidence'], reverse=True)[:8]
    
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
                'extraction_method': 'enhanced_simple'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

# Test với nội dung thực tế
def test_with_salary_content():
    """Test với nội dung lương thực tế"""
    extractor = EnhancedSimpleExtractor()
    
    # Nội dung mẫu từ debug
    salary_content = """
    1. Định mức giờ dạy/năm học đối với giáo viên mầm non; định mức tiết dạy/năm học đối với giáo viên phổ thông: 200 tiết
    2. Tiền lương của một tháng làm căn cứ tính trả tiền lương dạy thêm giờ của nhà giáo bao gồm: tiền lương tính theo hệ số lương
    3. Tổng số tiết dạy thêm trong một năm học của mỗi nhà giáo được tính để trả tiền lương dạy thêm giờ không quá 200 tiết
    4. Mức lương cơ bản: 1.800.000 đồng/tháng
    5. Tỷ lệ trả lương dạy thêm: 50% mức lương cơ bản
    """
    
    print("TEST ENHANCED SIMPLE EXTRACTOR")
    print("=" * 50)
    
    formulas = extractor.extract_formulas(salary_content)
    
    if formulas:
        print(f"Found {len(formulas)} formulas:")
        for i, formula in enumerate(formulas, 1):
            print(f"\n{i}. [{formula['confidence']:.2f}] {formula['name']}")
            print(f"   Formula: {formula['formula']}")
            print(f"   Type: {formula['type']}")
    else:
        print("No formulas found")
    
    return len(formulas) > 0

async def test_with_real_page():
    """Test với trang thực tế"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    extractor = EnhancedSimpleExtractor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            result = await extractor.extract_from_page(page, url)
            
            print(f"\nREAL PAGE TEST:")
            print(f"Content length: {result.get('content_length', 0)}")
            print(f"Formulas found: {result.get('total_formulas', 0)}")
            
            if result.get('formulas'):
                for i, formula in enumerate(result['formulas'], 1):
                    print(f"\n{i}. [{formula['confidence']:.2f}] {formula['name']}")
                    print(f"   Formula: {formula['formula'][:100]}...")
                    print(f"   Type: {formula['type']}")
            
            return result.get('total_formulas', 0) > 0
            
        finally:
            await browser.close()

if __name__ == "__main__":
    # Test với nội dung mẫu
    content_success = test_with_salary_content()
    
    # Test với trang thực tế
    page_success = asyncio.run(test_with_real_page())
    
    print(f"\n{'='*50}")
    print(f"SUMMARY:")
    print(f"Content test: {'PASSED' if content_success else 'FAILED'}")
    print(f"Page test: {'PASSED' if page_success else 'FAILED'}")
    print(f"Overall: {'SUCCESS' if (content_success or page_success) else 'NEEDS MORE WORK'}")
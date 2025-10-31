#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phân biệt Công thức vs Tham số"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class FormulaParameterExtractor:
    def __init__(self):
        # Patterns cho CÔNG THỨC (có phép tính)
        self.formula_patterns = [
            # Công thức có dấu = với phép tính
            {
                'pattern': r'([^.]{10,80})\s*=\s*([^.]{10,120}[×*+\-/][^.]{5,80})',
                'confidence': 0.95,
                'type': 'calculation_formula'
            },
            
            # Công thức có × hoặc /
            {
                'pattern': r'([^.]{10,60})\s*=\s*([^.]{5,60})\s*[×*/]\s*([^.]{5,60})',
                'confidence': 0.9,
                'type': 'multiplication_division'
            },
            
            # Công thức có []
            {
                'pattern': r'([^.]{10,60})\s*=\s*\[([^\]]{10,100})\]\s*[-+]\s*([^.]{5,60})',
                'confidence': 0.85,
                'type': 'bracket_formula'
            }
        ]
        
        # Patterns cho THAM SỐ (giá trị cụ thể)
        self.parameter_patterns = [
            # Không quá + số
            {
                'pattern': r'(không\s*quá)\s*([\d.,]+)\s*(tiết|đồng|%)',
                'confidence': 0.8,
                'type': 'limit_parameter'
            },
            
            # Tỷ lệ % cụ thể
            {
                'pattern': r'([\d.,]+)\s*%',
                'confidence': 0.7,
                'type': 'percentage_parameter'
            },
            
            # Mức cụ thể
            {
                'pattern': r'(mức\s+[^:=]{5,50})\s*[=:]\s*([\d.,]+\s*(?:đồng|tiết))',
                'confidence': 0.75,
                'type': 'amount_parameter'
            }
        ]
    
    def is_valid_formula(self, text: str) -> bool:
        """Kiểm tra có phải công thức thực sự"""
        # Phải có phép tính
        has_calculation = any(op in text for op in ['×', '*', '/', '+', '-', '='])
        
        # Phải có từ khóa liên quan
        has_keyword = any(word in text.lower() for word in 
                         ['tiền', 'lương', 'tiết', 'tổng', 'tính', 'bằng'])
        
        # Không phải số văn bản
        not_document_number = not re.search(r'\d+/\d+/[A-Z-]+', text)
        
        return has_calculation and has_keyword and not_document_number and 20 <= len(text) <= 200
    
    def is_valid_parameter(self, text: str) -> bool:
        """Kiểm tra có phải tham số"""
        # Có số cụ thể
        has_number = re.search(r'\d', text)
        
        # Có từ khóa
        has_keyword = any(word in text.lower() for word in 
                         ['không quá', 'mức', 'tỷ lệ', '%', 'đồng', 'tiết'])
        
        # Không có phép tính phức tạp
        no_complex_calc = not any(op in text for op in ['×', '*', '/', '(', ')', '[', ']'])
        
        return has_number and has_keyword and no_complex_calc and 10 <= len(text) <= 100
    
    def extract_formulas_and_parameters(self, text: str) -> Dict:
        """Trích xuất và phân loại"""
        if not text:
            return {"formulas": [], "parameters": []}
        
        formulas = []
        parameters = []
        
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Tìm CÔNG THỨC
        for pattern_info in self.formula_patterns:
            matches = re.finditer(pattern_info['pattern'], clean_text, re.IGNORECASE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                if self.is_valid_formula(formula_text):
                    name = match.group(1).strip()[:50] if match.groups() else "Công thức"
                    
                    formulas.append({
                        'name': name,
                        'formula': formula_text,
                        'type': pattern_info['type'],
                        'confidence': pattern_info['confidence']
                    })
        
        # Tìm THAM SỐ
        for pattern_info in self.parameter_patterns:
            matches = re.finditer(pattern_info['pattern'], clean_text, re.IGNORECASE)
            
            for match in matches:
                param_text = match.group(0).strip()
                
                if self.is_valid_parameter(param_text):
                    name = match.group(1).strip()[:50] if match.groups() else "Tham số"
                    value = match.group(2).strip() if len(match.groups()) > 1 else ""
                    
                    parameters.append({
                        'name': name,
                        'value': value,
                        'full_text': param_text,
                        'type': pattern_info['type'],
                        'confidence': pattern_info['confidence']
                    })
        
        # Loại bỏ trùng lặp
        formulas = self.deduplicate(formulas, 'formula')
        parameters = self.deduplicate(parameters, 'full_text')
        
        return {
            "formulas": sorted(formulas, key=lambda x: x['confidence'], reverse=True)[:5],
            "parameters": sorted(parameters, key=lambda x: x['confidence'], reverse=True)[:5]
        }
    
    def deduplicate(self, items: List[Dict], key: str) -> List[Dict]:
        """Loại bỏ trùng lặp"""
        seen = set()
        unique = []
        for item in items:
            item_key = item[key].lower().strip()
            if item_key not in seen:
                seen.add(item_key)
                unique.append(item)
        return unique
    
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
            
            result = self.extract_formulas_and_parameters(content)
            
            return {
                'url': url,
                'content_length': len(content),
                'formulas': result['formulas'],
                'parameters': result['parameters'],
                'total_formulas': len(result['formulas']),
                'total_parameters': len(result['parameters']),
                'extraction_method': 'formula_parameter_separation'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'parameters': [],
                'total_formulas': 0,
                'total_parameters': 0
            }

async def main():
    """Test phân biệt công thức vs tham số"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    extractor = FormulaParameterExtractor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            print("🔍 PHÂN BIỆT CÔNG THỨC vs THAM SỐ")
            print("=" * 60)
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            result = await extractor.extract_from_page(page, url)
            
            print(f"📄 Content length: {result.get('content_length', 0)}")
            print(f"🧮 Formulas: {result.get('total_formulas', 0)}")
            print(f"📊 Parameters: {result.get('total_parameters', 0)}")
            
            # Hiển thị CÔNG THỨC
            if result.get('formulas'):
                print(f"\n🧮 CÔNG THỨC (có phép tính):")
                for i, formula in enumerate(result['formulas'], 1):
                    print(f"{i}. [{formula['confidence']:.2f}] {formula['name']}")
                    print(f"   Formula: {formula['formula']}")
                    print(f"   Type: {formula['type']}")
                    print()
            
            # Hiển thị THAM SỐ
            if result.get('parameters'):
                print(f"📊 THAM SỐ (giá trị cụ thể):")
                for i, param in enumerate(result['parameters'], 1):
                    print(f"{i}. [{param['confidence']:.2f}] {param['name']}")
                    print(f"   Value: {param['value']}")
                    print(f"   Full: {param['full_text']}")
                    print(f"   Type: {param['type']}")
                    print()
            
            # Lưu kết quả
            output_file = Path("data/formulas_vs_parameters.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved to: {output_file}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
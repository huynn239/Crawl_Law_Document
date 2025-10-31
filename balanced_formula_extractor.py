#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balanced Formula Extractor - Cân bằng giữa độ chính xác và recall"""
import re
import json
import asyncio
from typing import Dict, List
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class BalancedFormulaExtractor:
    def __init__(self):
        self.patterns = [
            # 1. Mức tiền với từ khóa
            {
                'pattern': r'(mức\s+(?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí|giảm\s*trừ)[^=:]{0,50})\s*[=:]\s*([\d.,]+)\s*(đồng(?:/(?:tháng|năm))?)',
                'confidence': 0.95,
                'type': 'amount'
            },
            
            # 2. Tỷ lệ với từ khóa
            {
                'pattern': r'(tỷ\s*lệ\s+(?:thuế|bảo\s*hiểm|phụ\s*cấp)[^:=]{0,40})\s*[=:]\s*([\d.,]+\s*%)',
                'confidence': 0.95,
                'type': 'rate'
            },
            
            # 3. Lệ phí cụ thể
            {
                'pattern': r'(lệ\s*phí\s+(?:cấp|gia\s*hạn)[^:]{5,50})\s*:\s*([\d.,]+)\s*(đồng)',
                'confidence': 0.9,
                'type': 'fee'
            },
            
            # 4. Công thức tính
            {
                'pattern': r'((?:thuế|lương|phụ\s*cấp)[^=]{5,40})\s*=\s*([^.]{10,60}(?:×|x|\*)[^.]{5,40})',
                'confidence': 0.85,
                'type': 'calculation'
            },
            
            # 5. Khoảng tiền
            {
                'pattern': r'(mức\s*phạt[^từ]{0,20})\s*từ\s*([\d.,]+)\s*đến\s*([\d.,]+)\s*(đồng)',
                'confidence': 0.8,
                'type': 'range'
            }
        ]
        
        # Từ khóa tích cực
        self.positive_keywords = [
            'mức', 'tỷ lệ', 'thuế', 'phí', 'lương', 'phụ cấp', 'bảo hiểm', 'lệ phí'
        ]
        
        # Patterns loại trừ
        self.exclude_patterns = [
            r'\d+/\d+/[A-Z-]+',      # Số văn bản
            r'điều\s*\d+',           # Điều luật  
            r'khoản\s*\d+',          # Khoản
            r'\d{1,2}/\d{1,2}/\d{4}', # Ngày tháng
            r'trang\s*\d+',          # Số trang
        ]
    
    def is_valid_formula(self, text: str) -> bool:
        """Kiểm tra cân bằng"""
        text_lower = text.lower()
        
        # Loại bỏ patterns không hợp lệ
        for pattern in self.exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Phải có từ khóa tích cực
        has_positive = any(keyword in text_lower for keyword in self.positive_keywords)
        
        # Phải có số
        has_number = re.search(r'\d', text)
        
        # Độ dài hợp lý
        length_ok = 15 <= len(text) <= 200
        
        return has_positive and has_number and length_ok
    
    def extract_formulas(self, text: str) -> List[Dict]:
        """Trích xuất cân bằng"""
        if not text or len(text) < 50:
            return []
        
        results = []
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        for pattern_info in self.patterns:
            matches = re.finditer(pattern_info['pattern'], clean_text, re.IGNORECASE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                if self.is_valid_formula(formula_text):
                    name = match.group(1).strip() if match.groups() else "Công thức"
                    
                    # Context
                    start, end = match.span()
                    context_start = max(0, start - 80)
                    context_end = min(len(clean_text), end + 80)
                    context = clean_text[context_start:context_end]
                    
                    results.append({
                        'name': name[:50],
                        'formula': formula_text,
                        'description': f"{pattern_info['type']} - {pattern_info['confidence']}",
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
        
        return sorted(unique_results, key=lambda x: x['confidence'], reverse=True)[:8]
    
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
            
            # Lấy nội dung
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
                'extraction_method': 'balanced'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

# Test function
def test_balanced_extractor():
    """Test với nội dung mẫu"""
    extractor = BalancedFormulaExtractor()
    
    test_cases = [
        "Mức lương cơ bản: 1.800.000 đồng/tháng",
        "Tỷ lệ thuế thu nhập cá nhân: 10%", 
        "Lệ phí cấp giấy phép lái xe: 135.000 đồng",
        "Tỷ lệ bảo hiểm xã hội: 8%",
        "Thuế = Thu nhập × 15%",
        "Mức phạt từ 500.000 đến 1.000.000 đồng",
        "Thông tư số 156/2011/TT-BTC",  # Should reject
        "Điều 5 Khoản 2",  # Should reject
    ]
    
    print("TEST BALANCED EXTRACTOR")
    print("=" * 40)
    
    success_count = 0
    for i, test_text in enumerate(test_cases, 1):
        formulas = extractor.extract_formulas(test_text)
        if formulas:
            success_count += 1
            print(f"{i}. ✓ {test_text}")
            print(f"   -> {formulas[0]['name']} ({formulas[0]['type']})")
        else:
            print(f"{i}. ✗ {test_text}")
    
    print(f"\nSuccess rate: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    return success_count >= 5

if __name__ == "__main__":
    test_balanced_extractor()
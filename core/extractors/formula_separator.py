#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Formula Separator - Phân tách thông minh công thức vs tham số"""
import re
import json
import sys
import os
from typing import Dict, List

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class SmartFormulaSeparator:
    def __init__(self):
        # Các loại CHẮC CHẮN là công thức
        self.formula_types = {
            'salary_calculation', 'fraction_formula', 'multiplication_formula',
            'division_formula', 'complex_calculation', 'conditional_formula'
        }
        
        # Các loại CHẮC CHẮN là tham số
        self.parameter_types = {
            'amount_definition', 'percentage_rate', 'tax_rate', 'allowance',
            'insurance_rate', 'fee', 'coefficient', 'deduction', 'interest_rate',
            'exchange_rate', 'value_range', 'index', 'quota_rate', 'min_max_amount'
        }
    
    def is_true_formula(self, item: Dict) -> bool:
        """Xác định có phải công thức thật không - Logic cải tiến"""
        formula = item.get('formula', '')
        formula_type = item.get('type', '')
        
        # 1. Kiểm tra type trước
        if formula_type in self.formula_types:
            return True
        if formula_type in self.parameter_types:
            return False
        
        # 2. Kiểm tra có phép toán phức tạp
        if self.has_complex_math(formula):
            return True
        
        # 3. Kiểm tra pattern đơn giản "Tên: Giá trị"
        if self.is_simple_definition(formula):
            return False
        
        return False
    
    def has_complex_math(self, text: str) -> bool:
        """Kiểm tra có phép toán phức tạp"""
        # Có ngoặc đơn với phép toán
        if '(' in text and ')' in text:
            bracket_content = re.search(r'\(([^)]+)\)', text)
            if bracket_content and any(op in bracket_content.group(1) for op in ['×', '*', '/', '+', '-']):
                return True
        
        # Có nhiều phép toán
        math_ops = ['×', '*', '/', '+', '-']
        op_count = sum(text.count(op) for op in math_ops)
        if op_count >= 2:
            return True
        
        # Có phép chia hoặc nhân với biến
        if re.search(r'[×*/]\s*[A-Za-zÀ-ỹ]', text):
            return True
        
        return False
    
    def is_simple_definition(self, text: str) -> bool:
        """Kiểm tra có phải định nghĩa đơn giản"""
        # Pattern: "Tên: Số" hoặc "Tên = Số"
        simple_patterns = [
            r'^[^:=]+[:=]\s*[0-9.,]+\s*(?:%|đồng|vnd|tiết|giờ|lần)?(?:/(?:tháng|năm|ngày))?$',
            r'^[^:=]+[:=]\s*từ\s*[0-9.,]+\s*đến\s*[0-9.,]+',
        ]
        
        for pattern in simple_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        
        return False
    
    def extract_clean_value(self, formula_text: str) -> str:
        """Trích xuất giá trị sạch"""
        # Tìm phần sau dấu : hoặc =
        match = re.search(r'[:=]\s*(.+)', formula_text)
        if match:
            value = match.group(1).strip()
            # Loại bỏ phần thừa
            value = re.sub(r'\s*\d+\.\s*.*$', '', value)  # Loại bỏ "8. Giảm trừ..."
            return value
        return formula_text
    
    def separate(self, data: Dict) -> Dict:
        """Tách riêng formulas và parameters"""
        all_items = data.get('formulas', [])
        
        formulas = []
        parameters = []
        
        for item in all_items:
            if self.is_true_formula(item):
                formulas.append(item)
            else:
                # Tạo parameter
                parameter = {
                    'name': item.get('name', '').strip(),
                    'value': self.extract_clean_value(item.get('formula', '')),
                    'type': item.get('type', ''),
                    'confidence': item.get('confidence', 0),
                    'context': item.get('context', '')[:100] + "..." if len(item.get('context', '')) > 100 else item.get('context', '')
                }
                parameters.append(parameter)
        
        return {
            'formulas': formulas,
            'parameters': parameters,
            'total_formulas': len(formulas),
            'total_parameters': len(parameters),
            'original_total': len(all_items),
            'separation_method': 'smart_type_based_detection'
        }

def main():
    """Test và lưu kết quả"""
    # Load dữ liệu
    with open('data/enhanced_patterns_test_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    separator = SmartFormulaSeparator()
    result = separator.separate(data)
    
    print("🎯 SMART FORMULA vs PARAMETER SEPARATION")
    print("=" * 60)
    print(f"📊 Original items: {result['original_total']}")
    print(f"🧮 True formulas: {result['total_formulas']}")
    print(f"📋 Parameters: {result['total_parameters']}")
    
    print(f"\n🧮 TRUE FORMULAS (Công thức có phép toán):")
    for i, formula in enumerate(result['formulas'], 1):
        print(f"{i:2d}. [{formula['confidence']:.2f}] {formula['name'][:50]}")
        print(f"    📝 {formula['formula'][:80]}...")
        print(f"    🏷️  {formula['type']}")
    
    print(f"\n📊 PARAMETERS (Tham số & Định nghĩa):")
    for i, param in enumerate(result['parameters'], 1):
        print(f"{i:2d}. [{param['confidence']:.2f}] {param['name'][:40]}")
        print(f"    💰 {param['value']}")
        print(f"    🏷️  {param['type']}")
    
    # Lưu kết quả
    with open('data/smart_separated_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: data/smart_separated_result.json")
    
    # Thống kê
    formula_types = {}
    param_types = {}
    
    for f in result['formulas']:
        t = f['type']
        formula_types[t] = formula_types.get(t, 0) + 1
    
    for p in result['parameters']:
        t = p['type']
        param_types[t] = param_types.get(t, 0) + 1
    
    print(f"\n📈 FORMULA TYPES:")
    for t, count in sorted(formula_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {t}: {count}")
    
    print(f"\n📊 PARAMETER TYPES:")
    for t, count in sorted(param_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {t}: {count}")
    
    return result

if __name__ == "__main__":
    main()
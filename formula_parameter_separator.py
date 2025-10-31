#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Formula vs Parameter Separator - Tách riêng công thức thật và tham số"""
import re
import json
import sys
import os
from typing import Dict, List, Tuple

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class FormulaParameterSeparator:
    def __init__(self):
        # Toán tử cho công thức thật
        self.math_operators = ['=', '+', '-', '×', '*', '/', '÷', '(', ')']
        
        # Từ khóa chỉ công thức tính toán
        self.formula_keywords = [
            'tính', 'bằng', 'được tính', 'theo công thức',
            'phép tính', 'tổng', 'chia', 'nhân', 'cộng', 'trừ'
        ]
        
        # Từ khóa chỉ tham số/định nghĩa
        self.parameter_keywords = [
            'mức', 'tỷ lệ', 'định mức', 'hệ số', 'thuế suất',
            'lãi suất', 'tỷ giá', 'chỉ số', 'lệ phí', 'phạt'
        ]
    
    def has_math_operations(self, text: str) -> bool:
        """Kiểm tra có phép toán thật không"""
        # Loại bỏ dấu = đơn thuần (chỉ định nghĩa)
        if text.count('=') == 1 and not any(op in text for op in ['+', '-', '×', '*', '/', '÷', '(', ')']):
            return False
        
        # Có phép toán phức tạp
        complex_ops = ['+', '-', '×', '*', '/', '÷', '(', ')']
        return any(op in text for op in complex_ops)
    
    def is_true_formula(self, item: Dict) -> bool:
        """Xác định có phải công thức thật không"""
        formula = item.get('formula', '')
        formula_type = item.get('type', '')
        
        # 1. Có phép toán phức tạp
        if self.has_math_operations(formula):
            return True
        
        # 2. Thuộc loại công thức tính toán
        calculation_types = [
            'salary_calculation', 'fraction_formula', 'multiplication_formula',
            'division_formula', 'complex_calculation', 'conditional_formula'
        ]
        if formula_type in calculation_types:
            return True
        
        # 3. Chứa từ khóa công thức
        formula_lower = formula.lower()
        if any(keyword in formula_lower for keyword in self.formula_keywords):
            return True
        
        return False
    
    def separate_formulas_parameters(self, data: Dict) -> Dict:
        """Tách riêng formulas và parameters"""
        all_items = data.get('formulas', [])
        
        true_formulas = []
        parameters = []
        
        for item in all_items:
            if self.is_true_formula(item):
                true_formulas.append(item)
            else:
                # Chuyển thành parameter format
                parameter = {
                    'name': item.get('name', ''),
                    'value': self.extract_value(item.get('formula', '')),
                    'original_formula': item.get('formula', ''),
                    'type': item.get('type', ''),
                    'confidence': item.get('confidence', 0),
                    'context': item.get('context', '')
                }
                parameters.append(parameter)
        
        return {
            'formulas': true_formulas,
            'parameters': parameters,
            'total_formulas': len(true_formulas),
            'total_parameters': len(parameters),
            'separation_method': 'smart_math_detection'
        }
    
    def extract_value(self, formula_text: str) -> str:
        """Trích xuất giá trị từ định nghĩa"""
        # Pattern: Tên: Giá trị hoặc Tên = Giá trị
        match = re.search(r'[:=]\s*([^.]+)', formula_text)
        if match:
            return match.group(1).strip()
        return formula_text

def test_separation():
    """Test với dữ liệu thực tế"""
    # Load dữ liệu từ file
    with open('data/enhanced_patterns_test_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    separator = FormulaParameterSeparator()
    result = separator.separate_formulas_parameters(data)
    
    print("🔍 FORMULA vs PARAMETER SEPARATION")
    print("=" * 50)
    print(f"📊 Original items: {data.get('total_formulas', 0)}")
    print(f"✅ True formulas: {result['total_formulas']}")
    print(f"📋 Parameters: {result['total_parameters']}")
    
    print(f"\n🧮 TRUE FORMULAS (Công thức thật):")
    for i, formula in enumerate(result['formulas'], 1):
        print(f"{i:2d}. [{formula['confidence']:.2f}] {formula['name']}")
        print(f"    📝 {formula['formula'][:100]}...")
        print(f"    🏷️  {formula['type']}")
    
    print(f"\n📊 PARAMETERS (Tham số):")
    for i, param in enumerate(result['parameters'], 1):
        print(f"{i:2d}. [{param['confidence']:.2f}] {param['name']}")
        print(f"    💰 Value: {param['value']}")
        print(f"    🏷️  Type: {param['type']}")
    
    # Save separated results
    with open('data/separated_formulas_parameters.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: data/separated_formulas_parameters.json")
    return result

if __name__ == "__main__":
    test_separation()
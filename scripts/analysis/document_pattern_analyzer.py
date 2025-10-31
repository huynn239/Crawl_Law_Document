#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Document Pattern Analyzer - Phân tích patterns từ files DOC/PDF"""
import sys
import os
import json
import re
from collections import defaultdict, Counter

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class DocumentPatternAnalyzer:
    def __init__(self):
        self.formula_patterns = []
        self.parameter_patterns = []
        self.common_structures = defaultdict(int)
        
    def analyze_document_content(self, content):
        """Phân tích nội dung văn bản để tìm patterns"""
        
        # Tìm các cấu trúc công thức phổ biến
        formula_indicators = [
            r'([A-Za-zÀ-ỹ\s]+)\s*=\s*([^.]+)',  # Name = Formula
            r'([A-Za-zÀ-ỹ\s]+)\s*:\s*([^.]+)',  # Name: Formula  
            r'Công thức\s*:\s*([^.]+)',          # Công thức: ...
            r'Cách tính\s*:\s*([^.]+)',          # Cách tính: ...
            r'\[([^\]]+)\]',                     # [Formula in brackets]
            r'=\s*\[([^\]]+)\]',                 # = [Complex formula]
        ]
        
        # Tìm các cấu trúc tham số
        parameter_indicators = [
            r'(\d+(?:\.\d+)?)\s*(đồng|%|tiết|giờ|ngày|tuần|tháng|năm)',
            r'Mức\s+([^:]+):\s*(\d+(?:\.\d+)?)',
            r'Tỷ lệ\s+([^:]+):\s*(\d+(?:\.\d+)?%?)',
            r'Định mức\s+([^:]+):\s*(\d+(?:\.\d+)?)',
            r'không quá\s+(\d+)\s*(tiết|giờ)',
        ]
        
        results = {
            'formulas': [],
            'parameters': [],
            'structures': {},
            'patterns_found': {}
        }
        
        # Phân tích công thức
        for pattern in formula_indicators:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 2:
                    name = match.group(1).strip()
                    formula = match.group(2).strip()
                    if len(name) > 3 and len(formula) > 5:
                        results['formulas'].append({
                            'name': name,
                            'formula': formula,
                            'pattern': pattern,
                            'full_match': match.group(0)
                        })
        
        # Phân tích tham số
        for pattern in parameter_indicators:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                results['parameters'].append({
                    'match': match.group(0),
                    'pattern': pattern,
                    'groups': match.groups()
                })
        
        # Phân tích cấu trúc chung
        structures = {
            'equals_sign': len(re.findall(r'=', content)),
            'brackets': len(re.findall(r'\[.*?\]', content)),
            'parentheses': len(re.findall(r'\(.*?\)', content)),
            'multiplication': len(re.findall(r'[×x*]', content)),
            'division': len(re.findall(r'[/÷]', content)),
            'percentage': len(re.findall(r'\d+%', content)),
            'numbers': len(re.findall(r'\d+(?:\.\d+)?', content))
        }
        
        results['structures'] = structures
        
        return results
    
    def generate_enhanced_patterns(self, analysis_results):
        """Tạo enhanced regex patterns từ kết quả phân tích"""
        
        enhanced_patterns = {
            'formulas': [],
            'parameters': [],
            'meta_info': {}
        }
        
        # Tạo patterns cho công thức dựa trên cấu trúc phát hiện
        if analysis_results['structures']['brackets'] > 0:
            enhanced_patterns['formulas'].append({
                'name': 'complex_bracket_formula',
                'pattern': r'([A-Za-zÀ-ỹ\s/]+)\s*=\s*\[([^\]]+)\]',
                'description': 'Công thức phức tạp với dấu ngoặc vuông'
            })
        
        if analysis_results['structures']['equals_sign'] > 5:
            enhanced_patterns['formulas'].append({
                'name': 'multi_line_formula',
                'pattern': r'([A-Za-zÀ-ỹ\s/]+)\s*=\s*([^.]{20,200})',
                'description': 'Công thức nhiều dòng'
            })
        
        # Tạo patterns cho tham số
        if analysis_results['structures']['percentage'] > 0:
            enhanced_patterns['parameters'].append({
                'name': 'percentage_values',
                'pattern': r'(\d+(?:\.\d+)?)\s*%',
                'description': 'Giá trị phần trăm'
            })
        
        if analysis_results['structures']['numbers'] > 10:
            enhanced_patterns['parameters'].append({
                'name': 'monetary_values',
                'pattern': r'(\d+(?:\.\d+)?)\s*(đồng|VND)',
                'description': 'Giá trị tiền tệ'
            })
        
        enhanced_patterns['meta_info'] = {
            'total_formulas_found': len(analysis_results['formulas']),
            'total_parameters_found': len(analysis_results['parameters']),
            'complexity_score': sum(analysis_results['structures'].values()) / 10
        }
        
        return enhanced_patterns
    
    def save_patterns_to_file(self, patterns, filename):
        """Lưu patterns vào file để sử dụng lại"""
        os.makedirs("data/patterns", exist_ok=True)
        filepath = f"data/patterns/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
        
        return filepath

def analyze_sample_document():
    """Phân tích văn bản mẫu hiện tại"""
    
    # Đọc nội dung từ file test
    with open("data/test_url_raw_content.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    analyzer = DocumentPatternAnalyzer()
    
    print("DOCUMENT PATTERN ANALYSIS")
    print("=" * 50)
    
    # Phân tích
    results = analyzer.analyze_document_content(content)
    
    print(f"📊 ANALYSIS RESULTS:")
    print(f"   Formulas found: {len(results['formulas'])}")
    print(f"   Parameters found: {len(results['parameters'])}")
    
    print(f"\n🔍 DOCUMENT STRUCTURES:")
    for structure, count in results['structures'].items():
        print(f"   {structure}: {count}")
    
    print(f"\n📝 SAMPLE FORMULAS:")
    for i, formula in enumerate(results['formulas'][:3], 1):
        print(f"   {i}. {formula['name']}")
        print(f"      Formula: {formula['formula'][:60]}...")
    
    print(f"\n📊 SAMPLE PARAMETERS:")
    for i, param in enumerate(results['parameters'][:3], 1):
        print(f"   {i}. {param['match']}")
    
    # Tạo enhanced patterns
    enhanced = analyzer.generate_enhanced_patterns(results)
    
    print(f"\n🚀 ENHANCED PATTERNS GENERATED:")
    print(f"   Formula patterns: {len(enhanced['formulas'])}")
    print(f"   Parameter patterns: {len(enhanced['parameters'])}")
    print(f"   Complexity score: {enhanced['meta_info']['complexity_score']:.1f}")
    
    # Lưu kết quả
    analyzer.save_patterns_to_file(results, "analysis_results.json")
    analyzer.save_patterns_to_file(enhanced, "enhanced_patterns.json")
    
    print(f"\n💾 FILES SAVED:")
    print(f"   - data/patterns/analysis_results.json")
    print(f"   - data/patterns/enhanced_patterns.json")
    
    return results, enhanced

if __name__ == "__main__":
    analyze_sample_document()
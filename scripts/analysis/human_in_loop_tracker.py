#!/usr/bin/env python3
"""
Human-in-the-Loop Pattern Tracker
Theo dõi các công thức Layer 2 tìm thấy để con người cải thiện Layer 1
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import re

class PatternTracker:
    def __init__(self, db_file='data/pattern_tracker.json'):
        self.db_file = db_file
        self.data = self.load_data()
    
    def load_data(self):
        """Load tracking data"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'layer2_findings': [],
            'suggested_patterns': [],
            'implemented_patterns': []
        }
    
    def save_data(self):
        """Save tracking data"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def track_layer2_finding(self, url, formula, method='layer_2_gemini'):
        """Ghi lại công thức mà Layer 2 tìm thấy"""
        finding = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'formula': formula,
            'method': method,
            'analyzed': False
        }
        self.data['layer2_findings'].append(finding)
        self.save_data()
        print(f"Tracked Layer 2 finding: {formula[:50]}...")
    
    def analyze_patterns(self, min_occurrences=3):
        """Phân tích patterns từ Layer 2 findings"""
        print(f"\nPHAN TICH PATTERNS (toi thieu {min_occurrences} lan):")
        
        # Group similar formulas
        pattern_groups = defaultdict(list)
        
        for finding in self.data['layer2_findings']:
            if finding.get('analyzed'):
                continue
                
            formula = finding['formula']
            
            # Detect common patterns
            patterns = self.detect_patterns(formula)
            for pattern in patterns:
                pattern_groups[pattern].append(finding)
        
        # Suggest new regex patterns
        suggestions = []
        for pattern, findings in pattern_groups.items():
            if len(findings) >= min_occurrences:
                suggestion = {
                    'pattern': pattern,
                    'regex_suggestion': self.generate_regex(pattern),
                    'examples': [f['formula'][:100] for f in findings[:3]],
                    'count': len(findings),
                    'confidence': min(1.0, len(findings) / 10.0)
                }
                suggestions.append(suggestion)
        
        # Save suggestions
        self.data['suggested_patterns'].extend(suggestions)
        
        # Mark findings as analyzed
        for finding in self.data['layer2_findings']:
            finding['analyzed'] = True
        
        self.save_data()
        
        # Display suggestions
        if suggestions:
            print(f"\nTIM THAY {len(suggestions)} PATTERN MOI:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n{i}. Pattern: {suggestion['pattern']}")
                print(f"   Regex: {suggestion['regex_suggestion']}")
                print(f"   Xuất hiện: {suggestion['count']} lần")
                print(f"   Ví dụ: {suggestion['examples'][0]}")
        else:
            print("Khong tim thay pattern moi nao.")
        
        return suggestions
    
    def detect_patterns(self, formula):
        """Phát hiện patterns trong công thức"""
        patterns = []
        
        # Pattern 1: [Tên]: [Giá trị]
        if re.search(r'[^:]+:\s*[^.]+', formula):
            patterns.append('name_colon_value')
        
        # Pattern 2: [Tên] = [Phép tính]
        if re.search(r'[^=]+=\s*[^.]+', formula):
            patterns.append('name_equals_calculation')
        
        # Pattern 3: Có chứa phần trăm
        if '%' in formula:
            patterns.append('percentage_formula')
        
        # Pattern 4: Có chứa dấu ngoặc
        if '(' in formula and ')' in formula:
            patterns.append('parentheses_formula')
        
        # Pattern 5: Có chứa phép nhân
        if any(op in formula for op in ['×', 'x', '*']):
            patterns.append('multiplication_formula')
        
        return patterns
    
    def generate_regex(self, pattern):
        """Tạo regex suggestion cho pattern"""
        regex_map = {
            'name_colon_value': r'([^:]+):\s*([^.]+)',
            'name_equals_calculation': r'([^=]+)=\s*([^.]+)',
            'percentage_formula': r'([^%]*\d+(?:[.,]\d+)?%[^.]*)',
            'parentheses_formula': r'([^(]*\([^)]+\)[^.]*)',
            'multiplication_formula': r'([^×x*]*[×x*][^.]*)'
        }
        return regex_map.get(pattern, r'([^.]+)')
    
    def generate_improvement_code(self):
        """Tạo code để cải thiện Layer 1"""
        suggestions = [s for s in self.data['suggested_patterns'] 
                      if not s.get('implemented', False)]
        
        if not suggestions:
            print("Khong co pattern moi de implement.")
            return
        
        print(f"\nCODE CAI THIEN LAYER 1:")
        print("# Thêm các patterns sau vào self.formula_patterns:")
        
        for suggestion in suggestions:
            print(f"re.compile(r\"{suggestion['regex_suggestion']}\", re.IGNORECASE),  # {suggestion['pattern']} ({suggestion['count']} cases)")
    
    def mark_implemented(self, pattern):
        """Đánh dấu pattern đã được implement"""
        for suggestion in self.data['suggested_patterns']:
            if suggestion['pattern'] == pattern:
                suggestion['implemented'] = True
        self.save_data()

def demo_human_in_loop():
    """Demo quy trình Human-in-the-Loop"""
    tracker = PatternTracker()
    
    # Giả lập Layer 2 findings
    sample_findings = [
        "Mức lương tối thiểu: 1.800.000 đồng/tháng",
        "Tỷ lệ hưởng: 150% tiền lương cơ bản", 
        "Số tiết tối đa: 200 tiết/năm học",
        "Mức phụ cấp: 50% lương cơ bản",
        "Tỷ lệ đóng góp: 8% thu nhập",
        "Định mức giảng dạy = (Số giờ/ngày) × (Số ngày/tuần)",
        "Tiền thưởng = Lương cơ bản × Hệ số thưởng"
    ]
    
    # Track findings
    for formula in sample_findings:
        tracker.track_layer2_finding(
            "https://example.com/test", 
            formula, 
            "layer_2_gemini"
        )
    
    # Analyze patterns
    suggestions = tracker.analyze_patterns(min_occurrences=2)
    
    # Generate improvement code
    tracker.generate_improvement_code()
    
    print(f"\nTHONG KE:")
    print(f"Layer 2 findings: {len(tracker.data['layer2_findings'])}")
    print(f"Suggested patterns: {len(tracker.data['suggested_patterns'])}")

if __name__ == "__main__":
    demo_human_in_loop()
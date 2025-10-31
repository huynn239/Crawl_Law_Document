#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug patterns để tìm lỗi"""
import re
from smart_formula_patterns import SmartFormulaPatterns

def debug_single_pattern():
    """Debug từng pattern một"""
    
    # Test text đơn giản
    test_text = "Mức lương cơ bản = 1.800.000 đồng/tháng"
    
    print(f"Debug text: {test_text}")
    print("=" * 50)
    
    patterns = SmartFormulaPatterns()
    all_patterns = patterns.get_comprehensive_patterns()
    
    print(f"Total patterns: {len(all_patterns)}")
    
    for i, pattern_info in enumerate(all_patterns, 1):
        print(f"\n{i}. Pattern: {pattern_info['name']}")
        print(f"   Type: {pattern_info['type']}")
        print(f"   Regex: {pattern_info['pattern']}")
        
        # Test pattern
        matches = list(re.finditer(pattern_info['pattern'], test_text, re.IGNORECASE))
        
        if matches:
            print(f"   MATCH! Found {len(matches)} matches:")
            for j, match in enumerate(matches, 1):
                print(f"      {j}. Full match: '{match.group(0)}'")
                print(f"         Groups: {match.groups()}")
        else:
            print(f"   No match")

def test_simple_patterns():
    """Test với patterns đơn giản"""
    
    test_cases = [
        "Mức lương cơ bản = 1.800.000 đồng/tháng",
        "Tỷ lệ thuế: 10%",
        "Phụ cấp = 20% × lương cơ bản",
        "Lệ phí: 135.000 đồng",
        "Từ 500.000 đến 1.000.000 đồng"
    ]
    
    # Simple patterns
    simple_patterns = [
        {
            'name': 'Mức = số đồng',
            'pattern': r'(mức\s+[^=]+)\s*=\s*([\d.,]+)\s*(đồng)',
            'test': 'Mức lương cơ bản = 1.800.000 đồng/tháng'
        },
        {
            'name': 'Tỷ lệ: số%',
            'pattern': r'(tỷ\s*lệ[^:]*)\s*:\s*([\d.,]+\s*%)',
            'test': 'Tỷ lệ thuế: 10%'
        },
        {
            'name': 'Phép nhân với %',
            'pattern': r'([^=]+)\s*=\s*([\d.,]+\s*%)\s*[×*]\s*([^.]+)',
            'test': 'Phụ cấp = 20% × lương cơ bản'
        },
        {
            'name': 'Lệ phí: số đồng',
            'pattern': r'(lệ\s*phí[^:]*)\s*:\s*([\d.,]+)\s*(đồng)',
            'test': 'Lệ phí: 135.000 đồng'
        },
        {
            'name': 'Từ số đến số đồng',
            'pattern': r'từ\s*([\d.,]+)\s*đến\s*([\d.,]+)\s*(đồng)',
            'test': 'Từ 500.000 đến 1.000.000 đồng'
        }
    ]
    
    print("Testing Simple Patterns")
    print("=" * 50)
    
    for pattern_info in simple_patterns:
        test_text = pattern_info['test']
        pattern = pattern_info['pattern']
        
        print(f"\nTest: {test_text}")
        print(f"Pattern: {pattern}")
        
        matches = list(re.finditer(pattern, test_text, re.IGNORECASE))
        
        if matches:
            print(f"MATCH! Found {len(matches)} matches:")
            for i, match in enumerate(matches, 1):
                print(f"   {i}. Full: '{match.group(0)}'")
                print(f"      Groups: {match.groups()}")
        else:
            print("No match")

def test_money_patterns():
    """Test patterns cho số tiền"""
    
    money_texts = [
        "1.800.000 đồng",
        "1,800,000 đồng",
        "1.800.000 đồng/tháng",
        "135.000 đồng",
        "2 triệu đồng",
        "1,5 tỷ đồng"
    ]
    
    money_patterns = [
        r'[\d]{1,3}(?:[.,][\d]{3})*(?:[.,][\d]{1,2})?\s*đồng',
        r'[\d.,]+\s*(?:triệu|tỷ)\s*đồng',
        r'[\d.,]+\s*đồng(?:/tháng|/năm)?'
    ]
    
    print("Testing Money Patterns")
    print("=" * 40)
    
    for text in money_texts:
        print(f"\nText: {text}")
        
        for i, pattern in enumerate(money_patterns, 1):
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                print(f"   Pattern {i} MATCH: {matches[0].group(0)}")
            else:
                print(f"   Pattern {i}: No match")

if __name__ == "__main__":
    print("DEBUG FORMULA PATTERNS")
    print("=" * 60)
    
    debug_single_pattern()
    print("\n" + "=" * 60)
    test_simple_patterns()
    print("\n" + "=" * 60)
    test_money_patterns()
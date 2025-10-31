#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Improved Patterns - Kiểm tra 4 patterns mới"""
import re
import sys
import os
from enhanced_regex_patterns import EnhancedRegexPatterns

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def test_improved_patterns():
    """Test với nội dung thực từ Thông tư 21/2025"""
    
    # Nội dung có các công thức multi-line và phức tạp
    test_content = """
    Điều 3. Cách tính tiền lương dạy thêm giờ
    
    2. Tiền lương 01 tiết dạy thêm giờ được tính như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, phổ thông, thường xuyên:
    
    Tiền lương 01 tiết dạy = 
    (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy hoặc dạy trẻ) 
    / 
    (Định mức tiết dạy/năm học × 52 tuần)
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học:
    
    Tiền lương 01 tiết dạy = 
    (Tổng tiền lương của 12 tháng × Định mức tiết dạy/năm học tính theo giờ hành chính × 44 tuần) 
    / 
    (Định mức tiết dạy/năm học × 1760 giờ × 52 tuần)
    
    3. Định mức tiết dạy/năm học:
    
    a) Định mức giờ dạy/năm học đối với giáo viên mầm non = 200 tiết
    
    b) Định mức tiết dạy/năm học của giáo viên mầm non = 
    (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Tiền lương 01 tiết dạy thêm = Tiền lương 01 tiết dạy × 150%
    
    5. Tiền lương dạy thêm giờ/năm = Số tiết × Tiền lương 01 tiết
    
    6. [Phụ cấp trách nhiệm] - (Mức lương cơ bản × 25%)
    
    7. Tổng số tiết dạy thêm trong một năm học không quá 200 tiết
    
    8. Thời gian công tác tối thiểu = 5 năm
    """
    
    print("🧪 TESTING IMPROVED PATTERNS")
    print("=" * 60)
    
    patterns = EnhancedRegexPatterns()
    found_formulas = []
    
    # Test từng pattern
    for i, pattern_info in enumerate(patterns.get_patterns()[:8], 1):  # Test 8 patterns đầu
        pattern = pattern_info['pattern']
        
        try:
            # Sử dụng re.DOTALL để bắt multi-line
            matches = re.finditer(pattern, test_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            
            for match in matches:
                match_text = match.group(0).strip()
                
                if not patterns.is_excluded(match_text) and len(match_text) > 10:
                    confidence = pattern_info['confidence'] + patterns.calculate_confidence_boost(match_text)
                    
                    found_formulas.append({
                        'pattern_id': i,
                        'name': pattern_info['name'],
                        'formula': match_text,
                        'type': pattern_info['type'],
                        'confidence': min(1.0, confidence),
                        'groups': match.groups()
                    })
                    
        except re.error as e:
            print(f"❌ Pattern {i} error: {e}")
    
    # Deduplicate
    unique_formulas = []
    seen = set()
    
    for formula in found_formulas:
        key = formula['formula'][:50].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_formulas.append(formula)
    
    # Sort by confidence
    unique_formulas.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"📊 RESULTS: Found {len(unique_formulas)} unique formulas")
    print()
    
    for i, formula in enumerate(unique_formulas, 1):
        print(f"{i:2d}. [{formula['confidence']:.2f}] Pattern #{formula['pattern_id']} - {formula['name']}")
        print(f"    🏷️  Type: {formula['type']}")
        print(f"    📝 Formula: {formula['formula'][:100]}...")
        if formula['groups']:
            print(f"    🔍 Groups: {formula['groups']}")
        print()
    
    # Phân tích theo type
    type_counts = {}
    for formula in unique_formulas:
        t = formula['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print("📈 FORMULA TYPES:")
    for t, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {t}: {count}")
    
    # Kiểm tra 4 patterns mới
    new_pattern_types = ['multi_line_formula', 'bracket_formula', 'compact_formula', 'unicode_math_formula']
    new_found = [f for f in unique_formulas if f['type'] in new_pattern_types]
    
    print(f"\n🆕 NEW PATTERNS PERFORMANCE:")
    print(f"   Found by new patterns: {len(new_found)}/{len(unique_formulas)}")
    
    for formula in new_found:
        print(f"   ✅ {formula['type']}: {formula['formula'][:60]}...")
    
    return len(unique_formulas), len(new_found)

if __name__ == "__main__":
    total, new_count = test_improved_patterns()
    print(f"\n🎯 SUMMARY: {total} total formulas, {new_count} from new patterns")
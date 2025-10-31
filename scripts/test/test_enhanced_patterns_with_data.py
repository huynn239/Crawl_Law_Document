#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Enhanced Patterns với dữ liệu thực tế"""
import json
import sys
import os
from pathlib import Path
from scripts.extract.super_enhanced_formula_extractor import SuperEnhancedFormulaExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def test_with_real_content():
    """Test với nội dung thực tế từ file JSON"""
    
    # Sample content from Vietnamese legal document about teacher salary
    real_content = """
    Điều 3. Cách tính tiền lương dạy thêm giờ
    
    1. Tiền lương của một tháng làm căn cứ tính trả tiền lương dạy thêm giờ của nhà giáo bao gồm: tiền lương tính theo hệ số lương (bao gồm phụ cấp thâm niên vượt khung nếu có) và các khoản phụ cấp chức vụ, phụ cấp trách nhiệm (nếu có).
    
    2. Tiền lương 01 tiết dạy thêm giờ được tính như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, phổ thông, thường xuyên, trung tâm giáo dục nghề nghiệp - giáo dục thường xuyên:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy hoặc dạy trẻ) / (Định mức tiết dạy/năm học × 52 tuần)
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học, cao đẳng sư phạm:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Định mức tiết dạy/năm học tính theo giờ hành chính × 44 tuần) / (Định mức tiết dạy/năm học × 1760 giờ × 52 tuần)
    
    3. Định mức tiết dạy/năm học:
    
    a) Định mức giờ dạy/năm học đối với giáo viên mầm non; định mức tiết dạy/năm học đối với giáo viên phổ thông: 200 tiết
    
    b) Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Mức lương cơ bản hiện hành: 1.800.000 đồng/tháng
    
    5. Tỷ lệ đóng bảo hiểm xã hội: 8%
    
    6. Tỷ lệ đóng bảo hiểm y tế: 1.5%
    
    7. Phụ cấp trách nhiệm = 25% × mức lương cơ bản
    
    8. Giảm trừ gia cảnh: 11.000.000 đồng/tháng
    
    9. Thuế suất thuế thu nhập cá nhân: 10%
    
    10. Lệ phí đăng ký hồ sơ: 500.000 đồng
    
    11. Mức phạt vi phạm hành chính: từ 1.000.000 đến 5.000.000 đồng
    
    12. Hệ số lương K = 2.34
    
    13. Tổng số tiết dạy thêm trong một năm học không quá 200 tiết
    
    14. Lãi suất cho vay ưu đãi: 6.5%/năm
    
    15. Tỷ giá USD: 24.500 đồng
    
    16. Chỉ số giá tiêu dùng tăng: 3.2%
    """
    
    print("🧪 TESTING SUPER ENHANCED FORMULA EXTRACTOR")
    print("=" * 60)
    print(f"📄 Content length: {len(real_content)} characters")
    
    extractor = SuperEnhancedFormulaExtractor()
    formulas = extractor.extract_formulas_from_text(real_content)
    
    print(f"\n🔍 EXTRACTION RESULTS:")
    print(f"📊 Total formulas found: {len(formulas)}")
    
    if formulas:
        print(f"\n📋 DETAILED RESULTS:")
        for i, formula in enumerate(formulas, 1):
            print(f"\n{i:2d}. [{formula['confidence']:.3f}] {formula['name']}")
            print(f"    📝 Formula: {formula['formula']}")
            print(f"    🏷️  Type: {formula['type']}")
            print(f"    🔧 Method: {formula['extraction_method']}")
            if formula.get('groups'):
                print(f"    📦 Groups: {formula['groups']}")
            print(f"    📍 Context: {formula['context'][:100]}...")
    
    # Analyze by type
    type_counts = {}
    confidence_stats = []
    
    for formula in formulas:
        formula_type = formula.get("type", "unknown")
        type_counts[formula_type] = type_counts.get(formula_type, 0) + 1
        confidence_stats.append(formula.get("confidence", 0))
    
    if type_counts:
        print(f"\n📊 FORMULA TYPES ANALYSIS:")
        for formula_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {formula_type}: {count} formulas")
    
    if confidence_stats:
        avg_confidence = sum(confidence_stats) / len(confidence_stats)
        high_conf = len([c for c in confidence_stats if c > 0.9])
        med_conf = len([c for c in confidence_stats if 0.7 <= c <= 0.9])
        low_conf = len([c for c in confidence_stats if c < 0.7])
        
        print(f"\n📈 CONFIDENCE STATISTICS:")
        print(f"   Average confidence: {avg_confidence:.3f}")
        print(f"   High confidence (>0.9): {high_conf}")
        print(f"   Medium confidence (0.7-0.9): {med_conf}")
        print(f"   Low confidence (<0.7): {low_conf}")
    
    # Save results to file
    output_file = Path("data/enhanced_patterns_test_result.json")
    result_data = {
        "test_content_length": len(real_content),
        "total_formulas": len(formulas),
        "formulas": formulas,
        "type_counts": type_counts,
        "confidence_stats": {
            "average": avg_confidence if confidence_stats else 0,
            "high_confidence_count": high_conf if confidence_stats else 0,
            "medium_confidence_count": med_conf if confidence_stats else 0,
            "low_confidence_count": low_conf if confidence_stats else 0
        },
        "extraction_method": "super_enhanced_25_patterns_test"
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print(f"\n{'='*60}")
    print(f"🎯 TEST COMPLETE - Found {len(formulas)} formulas with avg confidence {avg_confidence:.3f}")
    
    return len(formulas) > 0

if __name__ == "__main__":
    success = test_with_real_content()
    print(f"\n🏆 Test {'PASSED' if success else 'FAILED'}")
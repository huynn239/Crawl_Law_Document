#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Extraction - Test trích xuất công thức"""
import sys
import os
import json
from core.extractors.production_extractor import ProductionReadyExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def test_extraction():
    """Test extraction với sample content"""
    
    # Sample content từ Thông tư 21/2025
    sample_content = """
    THÔNG TƯ 21/2025
    Quy định chế độ trả tiền lương dạy thêm giờ cho nhà giáo trong các cơ sở giáo dục công lập
    
    Điều 3. Cách tính tiền lương dạy thêm giờ
    
    1. Tiền lương của một tháng làm căn cứ tính trả tiền lương dạy thêm giờ của nhà giáo bao gồm: tiền lương tính theo hệ số lương (bao gồm phụ cấp thâm niên vượt khung nếu có) và các khoản phụ cấp chức vụ, phụ cấp trách nhiệm (nếu có).
    
    2. Tiền lương 01 tiết dạy thêm giờ được tính như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, phổ thông, thường xuyên:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy hoặc dạy trẻ) / (Định mức tiết dạy/năm học × 52 tuần)
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học, cao đẳng sư phạm:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Định mức tiết dạy/năm học tính theo giờ hành chính × 44 tuần) / (Định mức tiết dạy/năm học × 1760 giờ × 52 tuần)
    
    3. Định mức tiết dạy/năm học:
    
    a) Định mức giờ dạy/năm học đối với giáo viên mầm non; định mức tiết dạy/năm học đối với giáo viên phổ thông: 200 tiết
    
    b) Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Tiền lương 01 tiết dạy thêm = Tiền lương 01 tiết dạy × 150%
    
    5. Tiền lương dạy thêm giờ/năm = Số tiết × Tiền lương 01 tiết
    
    6. Tổng số tiết dạy thêm trong một năm học không quá 200 tiết
    
    7. Mức lương cơ bản hiện hành: 1.800.000 đồng/tháng
    
    8. Tỷ lệ đóng bảo hiểm xã hội: 8%
    
    9. Tỷ lệ đóng bảo hiểm y tế: 1.5%
    
    10. Phụ cấp trách nhiệm = 25% × mức lương cơ bản
    
    11. Giảm trừ gia cảnh: 11.000.000 đồng/tháng
    
    12. Thuế suất thuế thu nhập cá nhân: 10%
    """
    
    print("TEST EXTRACTION - Production Ready Extractor")
    print("=" * 60)
    print(f"Content length: {len(sample_content):,} chars")
    
    # Extract
    extractor = ProductionReadyExtractor()
    result = extractor.extract_from_text(sample_content)
    
    print(f"\nRESULTS:")
    print(f"   Formulas: {result['total_formulas']}")
    print(f"   Parameters: {result['total_parameters']}")
    print(f"   Method: {result['extraction_method']}")
    print(f"   Filtered: {result.get('filter_applied', False)}")
    
    if result['total_formulas'] > 0:
        print(f"\nTOP FORMULAS:")
        for i, formula in enumerate(result['formulas'][:5], 1):
            print(f"{i}. [{formula['confidence']:.2f}] {formula['name']}")
            print(f"   {formula['formula'][:80]}...")
            print(f"   Type: {formula['type']}")
    
    if result['total_parameters'] > 0:
        print(f"\nTOP PARAMETERS:")
        for i, param in enumerate(result['parameters'][:5], 1):
            print(f"{i}. [{param['confidence']:.2f}] {param['name']}")
            print(f"   {param.get('value', param.get('formula', ''))[:60]}...")
            print(f"   Type: {param['type']}")
    
    # Save result
    os.makedirs("data", exist_ok=True)
    with open("data/test_extraction_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\nResult saved to: data/test_extraction_result.json")
    return result

if __name__ == "__main__":
    test_extraction()
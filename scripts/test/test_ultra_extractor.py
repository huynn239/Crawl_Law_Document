#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Ultra Extractor với nội dung thực tế"""
import sys
from scripts.extract.ultra_formula_extractor import UltraFormulaExtractor

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_ultra_extractor():
    """Test với nội dung thực tế từ văn bản pháp luật"""
    
    extractor = UltraFormulaExtractor()
    
    # Test cases thực tế
    test_cases = [
        {
            "title": "Thông tư thuế thu nhập cá nhân",
            "content": """
            Điều 5. Mức giảm trừ gia cảnh
            1. Mức giảm trừ gia cảnh cho người nộp thuế là 11.000.000 đồng/tháng.
            2. Mức giảm trừ gia cảnh cho mỗi người phụ thuộc là 4.400.000 đồng/tháng.
            
            Điều 6. Thuế suất thuế thu nhập cá nhân
            - Đối với thu nhập từ 0 đến 5.000.000 đồng: Tỷ lệ thuế 5%
            - Đối với thu nhập từ 5.000.001 đến 10.000.000 đồng: Tỷ lệ thuế 10%
            
            Điều 7. Cách tính thuế
            Thuế thu nhập cá nhân phải nộp = Thu nhập tính thuế × Tỷ lệ thuế
            """
        },
        
        {
            "title": "Nghị định bảo hiểm xã hội",
            "content": """
            Điều 10. Mức đóng bảo hiểm
            1. Mức đóng bảo hiểm xã hội bằng 8% mức lương đóng bảo hiểm.
            2. Tỷ lệ bảo hiểm y tế: 1,5% mức lương đóng bảo hiểm.
            3. Tỷ lệ bảo hiểm thất nghiệp: 1% mức lương đóng bảo hiểm.
            
            Điều 11. Lương tối thiểu vùng
            - Vùng I: Mức lương tối thiểu 4.680.000 đồng/tháng
            - Vùng II: Mức lương tối thiểu 4.160.000 đồng/tháng
            """
        },
        
        {
            "title": "Thông tư phí lệ phí",
            "content": """
            Điều 2. Lệ phí cấp giấy phép lái xe
            1. Lệ phí cấp giấy phép lái xe hạng A1: 135.000 đồng
            2. Lệ phí cấp giấy phép lái xe hạng B1: 270.000 đồng
            3. Lệ phí gia hạn giấy phép lái xe: 50.000 đồng
            
            Điều 3. Phí sát hạch
            Phí sát hạch lái xe = Phí lý thuyết + Phí thực hành
            """
        },
        
        {
            "title": "Nghị định xử phạt",
            "content": """
            Điều 15. Mức phạt tiền
            1. Mức phạt vi phạm giao thông từ 800.000 đến 1.200.000 đồng
            2. Mức phạt vi phạm môi trường từ 2.000.000 đến 5.000.000 đồng
            
            Điều 16. Tính phạt bổ sung
            Phạt bổ sung = 10% × Giá trị hàng hóa vi phạm
            """
        },
        
        {
            "title": "Văn bản có số hiệu (test false positive)",
            "content": """
            Căn cứ Thông tư số 156/2011/TT-BTC ngày 14/11/2011 của Bộ Tài chính.
            Căn cứ Nghị định số 38/2019/NĐ-CP ngày 10/5/2019 của Chính phủ.
            Theo Điều 5 Khoản 2 Mục a của Luật số 123/2020/QH14.
            Trang 15/20 của tài liệu hướng dẫn.
            """
        }
    ]
    
    print("TEST ULTRA FORMULA EXTRACTOR")
    print("=" * 60)
    
    total_found = 0
    successful_docs = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['title']}")
        print("-" * 50)
        
        formulas = extractor.extract_formulas(test_case['content'])
        
        if formulas:
            successful_docs += 1
            total_found += len(formulas)
            print(f"✓ Found {len(formulas)} formulas:")
            
            for j, formula in enumerate(formulas, 1):
                print(f"  {j}. [{formula['confidence']:.2f}] {formula['name']}")
                print(f"     Formula: {formula['formula']}")
                print(f"     Type: {formula['type']}")
                print()
        else:
            print("✗ No formulas found (good if testing false positives)")
    
    print("=" * 60)
    print("SUMMARY")
    print(f"Documents tested: {len(test_cases)}")
    print(f"Successful extractions: {successful_docs} ({successful_docs/len(test_cases)*100:.1f}%)")
    print(f"Total formulas found: {total_found}")
    print(f"Average per document: {total_found/len(test_cases):.1f}")
    
    # Test individual patterns
    print(f"\nTEST INDIVIDUAL PATTERNS")
    print("-" * 30)
    
    individual_tests = [
        "Mức lương cơ bản: 1.800.000 đồng/tháng",
        "Tỷ lệ thuế thu nhập cá nhân: 10%",
        "Lệ phí cấp giấy phép lái xe: 135.000 đồng",
        "Mức phạt từ 500.000 đến 1.000.000 đồng",
        "Thuế = Thu nhập × 15%",
        "Thông tư số 156/2011/TT-BTC",  # Should be rejected
        "Điều 5 Khoản 2",  # Should be rejected
    ]
    
    pattern_success = 0
    for test_text in individual_tests:
        formulas = extractor.extract_formulas(test_text)
        if formulas:
            pattern_success += 1
            print(f"✓ {test_text} -> {formulas[0]['name']}")
        else:
            print(f"✗ {test_text}")
    
    print(f"\nPattern success rate: {pattern_success}/{len(individual_tests)} ({pattern_success/len(individual_tests)*100:.1f}%)")
    
    return total_found > 0 and successful_docs >= 3

if __name__ == "__main__":
    success = test_ultra_extractor()
    print(f"\nOVERALL TEST: {'PASSED' if success else 'FAILED'}")
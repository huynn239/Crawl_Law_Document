#!/usr/bin/env python3
"""Test enhanced salary formula extraction"""

import asyncio
import json
from ultimate_formula_extractor import UltimateFormulaExtractor

async def test_salary_formulas():
    extractor = UltimateFormulaExtractor()
    
    # Sample text with salary formulas from the actual document
    sample_text = """
    Điều 5. Tiền lương dạy thêm giờ
    
    1. Tiền lương 01 tiết dạy của nhà giáo được xác định như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, cơ sở giáo dục phổ thông:
    
    Tiền lương 01 tiết dạy | = | Tổng tiền lương của 12 tháng trong năm học | × | Số tuần giảng dạy
    ---|---|---|---|---
    Định mức tiết dạy/năm học | 52 tuần
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học:
    
    Tiền lương 01 tiết dạy | = | Tổng tiền lương của 12 tháng | × | Định mức tiết dạy/năm học | × | 44 tuần
    ---|---|---|---|---|---|---
    Định mức tiết dạy/năm học | 1760 giờ | 52 tuần
    
    2. Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm
    
    3. Số tiết dạy thêm của nhà giáo/năm học = (Tổng số tiết dạy được tính thực tế/năm học) - (Định mức tiết dạy/năm học)
    """
    
    result = await extractor.extract_formulas(text=sample_text)
    
    # Save results
    with open('data/salary_formulas_test.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Found {result['total_formulas']} formulas:")
    for i, formula in enumerate(result['formulas'], 1):
        print(f"{i}. {formula['name'][:60]}...")
        print(f"   Type: {formula['type']}")
        print(f"   Confidence: {formula['confidence']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_salary_formulas())
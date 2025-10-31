#!/usr/bin/env python3
"""
Simple test for hybrid formula extractor
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from scripts.extract.hybrid_formula_extractor import HybridFormulaExtractor

async def test_hybrid():
    load_dotenv()
    
    # Test with sample Vietnamese legal text
    sample_text = """
    Điều 3. Số tiết dạy thêm của nhà giáo được xác định như sau:
    
    1. Số tiết dạy thêm của nhà giáo/năm học = (Tổng số tiết dạy được tính thực tế/năm học) - (Định mức tiết dạy/năm học)
    
    2. Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm
    
    3. Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Số tiết dạy thêm không quá 200 tiết/năm học.
    
    5. Mức lương cơ bản tối thiểu là 1.800.000 đồng/tháng.
    """
    
    # Initialize extractor
    openai_key = os.getenv('OPENAI_API_KEY')
    extractor = HybridFormulaExtractor(openai_api_key=openai_key, use_crawl4ai=False)
    
    # Extract formulas
    result = extractor.extract_formulas(sample_text)
    
    # Add metadata
    result.update({
        'url': 'https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx',
        'content_length': len(sample_text)
    })
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/hybrid_test_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Hybrid extraction completed!")
    print(f"Found {result['total_formulas']} formulas, {result['total_parameters']} parameters")
    print(f"Results saved to: {output_file}")
    
    # Display results
    for i, formula in enumerate(result['formulas'], 1):
        print(f"\n{i}. {formula['name'][:60]}")
        print(f"   Formula: {formula['formula'][:100]}")
        print(f"   Type: {formula['type']}")
        print(f"   Confidence: {formula['confidence']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_hybrid())
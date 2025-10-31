#!/usr/bin/env python3
"""Test adaptive extractor with sample content from the real document"""

import asyncio
import json
import os
from scripts.extract.adaptive_formula_extractor import AdaptiveFormulaExtractor

async def test_with_sample():
    extractor = AdaptiveFormulaExtractor()
    
    # Nội dung mẫu từ văn bản thực Thông tư 21/2025
    sample_content = """
    THÔNG TƯ
    Quy định chế độ trả tiền lương dạy thêm giờ đối với nhà giáo trong các cơ sở giáo dục công lập
    
    Điều 5. Tiền lương dạy thêm giờ
    
    1. Tiền lương 01 tiết dạy của nhà giáo được xác định như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, cơ sở giáo dục phổ thông, cơ sở giáo dục thường xuyên, trường dự bị đại học, trường chuyên biệt và nhà giáo giáo dục nghề nghiệp:
    
    Tiền lương 01 tiết dạy | = | Tổng tiền lương của 12 tháng trong năm học | × | Số tuần giảng dạy hoặc dạy trẻ (không bao gồm số tuần dự phòng)
    ---|---|---|---|---
    Định mức tiết dạy/năm học | 52 tuần
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học, cao đẳng sư phạm, cơ sở đào tạo, bồi dưỡng của Bộ, cơ quan ngang Bộ, cơ quan thuộc Chính phủ, tổ chức chính trị, tổ chức chính trị - xã hội, trường chính trị của tỉnh, thành phố trực thuộc Trung ương:
    
    Tiền lương 01 tiết dạy | = | Tổng tiền lương của 12 tháng trong năm học | × | Định mức tiết dạy/năm học tính theo giờ hành chính | × | 44 tuần
    ---|---|---|---|---|---|---
    Định mức tiết dạy/năm học | 1760 giờ | 52 tuần
    
    2. Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm
    
    Điều 4. Tổng số tiết dạy thêm trong một năm học
    
    1. Tổng số tiết dạy thêm = Tổng số tiết dạy được tính để thực hiện các nhiệm vụ khác/năm học - Tổng định mức tiết dạy của tất cả nhà giáo/năm học
    
    2. Số tiết dạy thêm của nhà giáo/năm học = (Tổng số tiết dạy được tính thực tế/năm học) - (Định mức tiết dạy/năm học)
    
    3. Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Số tiết dạy thêm không quá 200 tiết/năm học.
    
    5. Mức lương cơ bản tối thiểu là 1.800.000 đồng/tháng.
    """
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    result = await extractor.extract_formulas(text=sample_content)
    result['url'] = url  # Add URL manually
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/adaptive_thongtu21_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Adaptive extraction completed!")
    print(f"Detected domain: {result.get('detected_domain', 'unknown')}")
    print(f"Found: {result['total_formulas']} formulas, {result['total_parameters']} parameters")
    print(f"Method: {result['extraction_method']}")
    print(f"Content length: {result['content_length']} characters")
    print(f"Results saved to: {output_file}")
    
    # Show formulas
    print(f"\nFormulas found:")
    for i, formula in enumerate(result['formulas'][:10], 1):
        name = formula['name'][:70] + "..." if len(formula['name']) > 70 else formula['name']
        print(f"{i}. {name}")
        print(f"   Type: {formula['type']} | Confidence: {formula['confidence']:.2f}")
    
    # Show parameters
    if result['parameters']:
        print(f"\nParameters found:")
        for i, param in enumerate(result['parameters'], 1):
            print(f"{i}. {param['name']} = {param.get('value', 'N/A')}")
            print(f"   Type: {param['type']} | Confidence: {param['confidence']:.2f}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_with_sample())
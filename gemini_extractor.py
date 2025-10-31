#!/usr/bin/env python3
"""
Gemini-powered formula extractor for Vietnamese legal documents
"""

import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class GeminiFormulaExtractor:
    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def extract_formulas(self, text: str, url: str = None) -> dict:
        """Extract formulas using Gemini 2.5 Pro"""
        
        prompt = f"""
Phân tích văn bản pháp luật Việt Nam sau và trích xuất TẤT CẢ các công thức tính toán, phép toán, và quy tắc tính toán.

VĂN BẢN:
{text}

YÊU CẦU:
1. Tìm tất cả công thức có dạng: A = B, A × B, A / B, A + B, A - B
2. Tìm các quy tắc tính toán có chứa số, phần trăm, đơn vị tiền tệ
3. Tìm các định mức, giới hạn, mức tối thiểu/tối đa
4. Bỏ qua số hiệu văn bản, ngày tháng, địa chỉ

ĐỊNH DẠNG TRƯỚC VỀ JSON:
{{
  "formulas": [
    {{
      "name": "Tên ngắn gọn của công thức",
      "formula": "Công thức đầy đủ",
      "type": "salary_calc|rate_calc|limit|percentage|amount",
      "confidence": 0.95,
      "context": "Ngữ cảnh xung quanh",
      "variables": ["biến1", "biến2"],
      "description": "Mô tả ý nghĩa công thức"
    }}
  ],
  "parameters": [
    {{
      "name": "Tên tham số",
      "value": "Giá trị",
      "unit": "Đơn vị",
      "type": "limit|minimum|maximum|rate",
      "confidence": 0.9
    }}
  ]
}}

Chỉ trả về JSON, không giải thích thêm.
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean JSON response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text)
            
            # Add metadata
            result.update({
                'url': url,
                'total_formulas': len(result.get('formulas', [])),
                'total_parameters': len(result.get('parameters', [])),
                'extraction_method': 'gemini_2_5_pro',
                'content_length': len(text)
            })
            
            return result
            
        except Exception as e:
            return {
                'formulas': [],
                'parameters': [],
                'error': str(e),
                'extraction_method': 'gemini_2_5_pro',
                'url': url,
                'total_formulas': 0,
                'total_parameters': 0,
                'content_length': len(text)
            }

async def test_gemini_extraction():
    """Test Gemini extraction with sample content"""
    
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
    
    extractor = GeminiFormulaExtractor()
    result = await extractor.extract_formulas(sample_content, url)
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/gemini_thongtu21_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Gemini extraction completed!")
    print(f"Found: {result['total_formulas']} formulas, {result['total_parameters']} parameters")
    print(f"Method: {result['extraction_method']}")
    print(f"Results saved to: {output_file}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_gemini_extraction())
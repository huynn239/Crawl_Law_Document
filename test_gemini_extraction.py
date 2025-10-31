#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Gemini Pro 2.5 cho trích xuất công thức"""
import asyncio
import os
from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_gemini_extraction():
    """Test với Gemini Pro 2.5"""
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Please set it first:")
        print("set GEMINI_API_KEY=your_api_key")
        return
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    # Prompt chuyên sâu cho Gemini
    gemini_prompt = """
    Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam về lương giáo viên.
    
    NHIỆM VỤ: Trích xuất TẤT CẢ công thức tính toán trong văn bản, đặc biệt:
    
    1. Công thức tính tiền lương 1 tiết dạy
    2. Công thức tính tiền lương dạy thêm giờ  
    3. Công thức tính tổng số tiết dạy thêm
    4. Các tỷ lệ phần trăm (150%, v.v.)
    5. Các giới hạn số lượng (200 tiết, v.v.)
    6. Công thức phân số phức tạp
    
    VÍ DỤ MONG MUỐN:
    - "Tiền lương 1 tiết dạy thêm = Tiền lương 1 tiết dạy × 150%"
    - "Không quá 200 tiết dạy thêm/năm học"
    - "Tiền lương 1 tiết dạy = (Tổng tiền lương 12 tháng × Số tuần) / (Định mức × 52)"
    
    Trả về JSON:
    {
      "formulas": [
        {
          "name": "tên công thức",
          "formula": "công thức đầy đủ",
          "description": "mô tả chi tiết",
          "context": "ngữ cảnh trong văn bản",
          "type": "loại công thức"
        }
      ],
      "total_formulas": số_lượng
    }
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Cấu hình Gemini
        llm_config = LLMConfig(
            provider="gemini/gemini-2.0-flash-exp",
            api_token=os.getenv("GEMINI_API_KEY")
        )
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            extraction_type="json",
            instruction=gemini_prompt
        )
        
        try:
            result = await crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
                js_code="""
                const tab1 = document.querySelector('#aNoiDung') || document.querySelector('a[href="#tab1"]');
                if (tab1) {
                    tab1.click();
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
                """,
                wait_for="networkidle"
            )
            
            if result.success:
                print("✅ Gemini Pro 2.5 SUCCESS!")
                print(f"Content length: {len(result.cleaned_html)}")
                
                extracted_data = result.extracted_content
                print(f"Response type: {type(extracted_data)}")
                
                if extracted_data:
                    import json
                    try:
                        if isinstance(extracted_data, str):
                            data = json.loads(extracted_data)
                        else:
                            data = extracted_data
                        
                        formulas = data.get("formulas", [])
                        print(f"\n🎯 Gemini found {len(formulas)} formulas:")
                        
                        for i, formula in enumerate(formulas, 1):
                            print(f"\n{i}. [{formula.get('type', 'unknown')}] {formula.get('name', 'N/A')}")
                            print(f"   Formula: {formula.get('formula', 'N/A')}")
                            print(f"   Description: {formula.get('description', 'N/A')}")
                            print(f"   Context: {formula.get('context', 'N/A')[:100]}...")
                        
                        # Lưu kết quả
                        output_file = "data/gemini_formulas.json"
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"\n💾 Saved to: {output_file}")
                        
                    except Exception as e:
                        print(f"❌ JSON parse error: {e}")
                        print("Raw response:", str(extracted_data)[:1000])
                else:
                    print("❌ No data extracted from Gemini")
                    
            else:
                print(f"❌ Crawl failed: {result.error_message}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_extraction())
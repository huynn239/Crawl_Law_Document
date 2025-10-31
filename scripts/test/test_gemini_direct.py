#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Gemini trực tiếp với nội dung ngắn"""
import asyncio
import os
from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_gemini_direct():
    """Test Gemini với nội dung trực tiếp"""
    
    # Set API key
    os.environ["GEMINI_API_KEY"] = "AIzaSyAinQHM649wj9BfQB3yp5-Q82Y4pssKXVU"
    
    # Nội dung mẫu từ văn bản thực
    sample_content = """
    Điều 5. Tiền lương dạy thêm giờ
    
    1. Tiền lương 01 tiết dạy của nhà giáo được xác định như sau:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy) / (Định mức tiết dạy/năm học × 52 tuần)
    
    2. Tiền lương 01 tiết dạy thêm = Tiền lương 01 tiết dạy × 150%.
    
    3. Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm.
    
    Điều 3. Quy định chung
    
    3. Tổng số tiết dạy thêm trong một năm học của mỗi nhà giáo
    a) Tổng số tiết dạy thêm trong một năm học của mỗi nhà giáo được tính để trả tiền lương dạy thêm giờ không quá 200 tiết.
    
    Điều 4. Tổng số tiết dạy thêm
    Tổng số tiết dạy thêm tối đa = [Tổng số tiết dạy + Tổng số tiết nhiệm vụ khác + Tổng số tiết dạy đủ] - (Tổng định mức tiết dạy của tất cả nhà giáo/năm học).
    """
    
    prompt = """
    Trích xuất TẤT CẢ công thức tính toán từ văn bản về lương giáo viên.
    
    Trả về JSON:
    {
      "formulas": [
        {
          "name": "tên công thức",
          "formula": "công thức đầy đủ", 
          "type": "loại"
        }
      ],
      "total_formulas": số_lượng
    }
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        llm_config = LLMConfig(
            provider="gemini/gemini-2.0-flash-exp",
            api_token=os.getenv("GEMINI_API_KEY")
        )
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            extraction_type="json",
            instruction=prompt
        )
        
        try:
            # Test với nội dung trực tiếp
            result = await crawler.arun(
                url="data:text/html,<html><body>" + sample_content.replace('\n', '<br>') + "</body></html>",
                extraction_strategy=extraction_strategy,
                bypass_cache=True
            )
            
            if result.success:
                print("✅ Gemini Direct Test SUCCESS!")
                
                extracted_data = result.extracted_content
                print(f"Response: {extracted_data}")
                
                if extracted_data:
                    import json
                    try:
                        if isinstance(extracted_data, str):
                            data = json.loads(extracted_data)
                        else:
                            data = extracted_data
                        
                        formulas = data.get("formulas", [])
                        print(f"\n🎯 Found {len(formulas)} formulas:")
                        
                        for i, formula in enumerate(formulas, 1):
                            print(f"{i}. {formula.get('name', 'N/A')}")
                            print(f"   {formula.get('formula', 'N/A')}")
                        
                    except Exception as e:
                        print(f"Parse error: {e}")
                        print("Raw:", str(extracted_data)[:500])
                else:
                    print("❌ No extraction")
                    
            else:
                print(f"❌ Failed: {result.error_message}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_direct())
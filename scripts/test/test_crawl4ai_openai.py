#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Crawl4AI với OpenAI"""
import asyncio
import os
from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field
from typing import List
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class Formula(BaseModel):
    name: str = Field(description="Tên công thức")
    formula: str = Field(description="Công thức tính toán")
    description: str = Field(description="Mô tả công thức")
    context: str = Field(description="Ngữ cảnh xung quanh công thức")

class FormulaExtraction(BaseModel):
    formulas: List[Formula] = Field(description="Danh sách các công thức tìm thấy")
    total_formulas: int = Field(description="Tổng số công thức")

async def test_crawl4ai_openai():
    """Test Crawl4AI với OpenAI"""
    
    # Set OpenAI API key (nếu có)
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Please set it to use OpenAI.")
        print("Example: set OPENAI_API_KEY=your_api_key")
        return
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    # Prompt tối ưu cho trích xuất công thức lương
    extraction_prompt = """
    Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam về lương và giáo dục.
    
    NHIỆM VỤ: Tìm và trích xuất TẤT CẢ các công thức, quy định về lương, tiền, tỷ lệ trong văn bản.
    
    Tìm các công thức dạng:
    - Mức lương = [số tiền] đồng
    - Tỷ lệ [tên]: [số]%
    - Định mức [tên]: [số] tiết/giờ
    - Không quá [số] tiết/đồng
    - Tiền lương bao gồm: [danh sách]
    - Căn cứ tính: [công thức]
    
    VÍ DỤ MONG MUỐN:
    - "Định mức tiết dạy/năm học: 200 tiết"
    - "Không quá 200 tiết dạy thêm"
    - "Tiền lương bao gồm: lương cơ bản + phụ cấp"
    - "Mức lương cơ bản: 1.800.000 đồng/tháng"
    
    KHÔNG lấy:
    - Số điều, khoản (Điều 1, Khoản 2)
    - Ngày tháng (23/9/2025)
    - Số văn bản (21/2025/TT-BGDĐT)
    
    Trả về JSON với format chính xác.
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Cấu hình OpenAI
        llm_config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=os.getenv("OPENAI_API_KEY")
        )
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=FormulaExtraction.model_json_schema(),
            extraction_type="schema",
            instruction=extraction_prompt
        )
        
        try:
            result = await crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
                js_code="""
                // Click tab nội dung
                const tab1 = document.querySelector('#aNoiDung') || document.querySelector('a[href="#tab1"]');
                if (tab1) {
                    tab1.click();
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
                """,
                wait_for="networkidle"
            )
            
            if result.success:
                print("✅ Crawl4AI + OpenAI SUCCESS!")
                print(f"Content length: {len(result.cleaned_html)}")
                
                extracted_data = result.extracted_content
                
                if extracted_data and isinstance(extracted_data, dict):
                    formulas = extracted_data.get("formulas", [])
                    print(f"Found {len(formulas)} formulas:")
                    
                    for i, formula in enumerate(formulas, 1):
                        print(f"\n{i}. {formula.get('name', 'N/A')}")
                        print(f"   Formula: {formula.get('formula', 'N/A')}")
                        print(f"   Description: {formula.get('description', 'N/A')}")
                        print(f"   Context: {formula.get('context', 'N/A')[:100]}...")
                else:
                    print("❌ No formulas extracted by LLM")
                    print(f"LLM response: {extracted_data}")
            else:
                print(f"❌ Crawl4AI failed: {result.error_message}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_crawl4ai_openai())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test với prompt cải tiến"""
import asyncio
import os
from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_improved_prompt():
    """Test với prompt đơn giản hơn"""
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    # Prompt đơn giản
    simple_prompt = """
    Tìm tất cả công thức tính lương, tiền, tỷ lệ trong văn bản.
    
    Tìm:
    - Mức lương: X đồng
    - Tỷ lệ: X%
    - Định mức: X tiết
    - Không quá X tiết/đồng
    
    Trả về JSON:
    {
      "formulas": [
        {
          "name": "tên công thức",
          "formula": "công thức đầy đủ",
          "description": "mô tả",
          "context": "ngữ cảnh"
        }
      ],
      "total_formulas": số_lượng
    }
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Thử với OpenAI trước
        if os.getenv("OPENAI_API_KEY"):
            llm_config = LLMConfig(
                provider="openai/gpt-4o-mini",
                api_token=os.getenv("OPENAI_API_KEY")
            )
            print("Using OpenAI GPT-4o-mini")
        else:
            # Fallback to Ollama
            llm_config = LLMConfig(
                provider="ollama/qwen:7b",
                api_token=None,
                base_url="http://localhost:11434"
            )
            print("Using Ollama qwen:7b")
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            extraction_type="json",
            instruction=simple_prompt
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
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
                """,
                wait_for="networkidle"
            )
            
            if result.success:
                print("✅ SUCCESS!")
                print(f"Content length: {len(result.cleaned_html)}")
                
                extracted_data = result.extracted_content
                print(f"LLM response type: {type(extracted_data)}")
                print(f"LLM response: {extracted_data}")
                
                if extracted_data:
                    # Thử parse JSON
                    import json
                    try:
                        if isinstance(extracted_data, str):
                            data = json.loads(extracted_data)
                        else:
                            data = extracted_data
                        
                        formulas = data.get("formulas", [])
                        print(f"\n🎯 Found {len(formulas)} formulas:")
                        
                        for i, formula in enumerate(formulas, 1):
                            print(f"\n{i}. {formula.get('name', 'N/A')}")
                            print(f"   Formula: {formula.get('formula', 'N/A')}")
                            print(f"   Description: {formula.get('description', 'N/A')}")
                            
                    except Exception as e:
                        print(f"❌ JSON parse error: {e}")
                        print("Raw response:", str(extracted_data)[:500])
                else:
                    print("❌ No data extracted")
                    
                    # Fallback: show sample content
                    content = result.cleaned_html
                    lines = content.split('\n')
                    salary_lines = [line.strip() for line in lines 
                                  if line.strip() and len(line.strip()) > 20 
                                  and any(word in line.lower() for word in ['lương', 'tiền', 'mức', 'tỷ lệ', 'tiết'])
                                  and any(char.isdigit() for char in line)]
                    
                    print(f"\n📋 Sample salary-related content ({len(salary_lines)} lines):")
                    for i, line in enumerate(salary_lines[:5], 1):
                        print(f"{i}. {line[:100]}...")
                        
            else:
                print(f"❌ Crawl failed: {result.error_message}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_improved_prompt())
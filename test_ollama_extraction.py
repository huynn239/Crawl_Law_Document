#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test LLM extraction với Ollama local"""
import sys
import asyncio
import json
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from tvpl_crawler.formula_extractor import FormulaExtraction

async def test_ollama_extraction():
    """Test với Ollama local model"""
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    print("Testing Ollama local LLM extraction...")
    print("Make sure Ollama is running: ollama serve")
    print("And model is available: ollama pull llama3.2")
    
    extraction_prompt = """
    Phân tích văn bản pháp luật Việt Nam và trích xuất TẤT CẢ các công thức tính toán.
    
    Tìm kiếm các loại công thức:
    1. Công thức tính lương, phụ cấp, trợ cấp (VD: Lương = X đồng, Phụ cấp = Y% × lương cơ bản)
    2. Công thức tính thuế, phí, lệ phí (VD: Thuế = thu nhập × 10%)
    3. Công thức tính tiền phạt, vi phạm (VD: Tiền phạt = 500.000 đồng + 2% × giá trị)
    4. Công thức tính tỷ lệ, phần trăm (VD: Tỷ lệ BHXH: 8%)
    5. Công thức có phép tính (+, -, ×, /, =, %)
    6. Mức quy định cụ thể (VD: Mức tối thiểu: 1.800.000 đồng)
    
    Với mỗi công thức, xác định:
    - Tên công thức (mô tả ngắn gọn)
    - Công thức đầy đủ (bao gồm số liệu và đơn vị)
    - Mô tả ý nghĩa của công thức
    - Ngữ cảnh (điều, khoản nào quy định)
    
    CHỈ trả về công thức có ý nghĩa tính toán thực sự, BỎ QUA:
    - Số điều, khoản, mục
    - Ngày tháng năm
    - Số văn bản
    - Địa chỉ, số điện thoại
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Cấu hình Ollama
        llm_config = LLMConfig(
            provider="ollama/qwen:7b",  # Qwen 7B - tốt cho tiếng Việt
            api_token=None,
            base_url="http://localhost:11434"  # Ollama default URL
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
                // Click tab nội dung (tab1)
                const tab1 = document.querySelector('#aNoiDung') || document.querySelector('a[href="#tab1"]');
                if (tab1) {
                    tab1.click();
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
                
                // Đợi nội dung load
                await new Promise(resolve => setTimeout(resolve, 3000));
                """,
                wait_for="networkidle"
            )
            
            if result.success:
                extracted_data = result.extracted_content
                if isinstance(extracted_data, str):
                    try:
                        extracted_data = json.loads(extracted_data)
                    except:
                        extracted_data = {"formulas": [], "total_formulas": 0}
                
                print(f"\n{'='*60}")
                print(f"Ollama Extraction Results:")
                print(f"Content length: {len(result.cleaned_html)}")
                print(f"Total formulas: {extracted_data.get('total_formulas', 0)}")
                
                formulas = extracted_data.get('formulas', [])
                if formulas:
                    print(f"\nFormulas found:")
                    for i, formula in enumerate(formulas, 1):
                        name = formula.get('name', 'N/A')
                        formula_text = formula.get('formula', '')
                        description = formula.get('description', '')
                        print(f"  {i}. {name}")
                        print(f"     Formula: {formula_text}")
                        print(f"     Description: {description}")
                        print()
                else:
                    print("No formulas found.")
                
                # Save results
                output_file = Path("data/test_ollama_extraction.json")
                result_data = {
                    "url": url,
                    "tab1_content_length": len(result.cleaned_html),
                    "formulas": formulas,
                    "total_formulas": len(formulas),
                    "extraction_method": "ollama_llm"
                }
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                print(f"Results saved to: {output_file}")
                
            else:
                print(f"✗ Crawl failed: {result.error_message}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            print("Make sure Ollama is running and llama3.2 model is available")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ollama_extraction())
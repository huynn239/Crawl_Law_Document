#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Qwen 7B với crawl4ai đơn giản"""
import asyncio
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy

async def test_qwen_simple():
    """Test Qwen 7B với prompt đơn giản"""
    
    # Prompt đơn giản không dùng JSON schema
    simple_prompt = """
    Tìm tất cả công thức tính toán trong văn bản này.
    
    Ví dụ công thức cần tìm:
    - Lương = 1.800.000 đồng
    - Phụ cấp = 20% × lương cơ bản
    - Thuế = thu nhập × 10%
    
    Chỉ liệt kê các công thức tìm được, mỗi công thức một dòng.
    """
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Cấu hình Qwen 7B
        llm_config = LLMConfig(
            provider="ollama/qwen:7b",
            api_token=None,
            base_url="http://localhost:8080"
        )
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            extraction_type="text",  # Dùng text thay vì schema
            instruction=simple_prompt
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
                print(f"✓ Crawl thành công")
                print(f"Content length: {len(result.cleaned_html)}")
                print(f"Extracted content type: {type(result.extracted_content)}")
                print(f"Extracted content: {result.extracted_content}")
                
                if result.extracted_content:
                    print("\n=== KẾT QUẢ TỪ QWEN 7B ===")
                    print(result.extracted_content)
                else:
                    print("❌ Qwen 7B trả về None")
                    
            else:
                print(f"✗ Crawl thất bại: {result.error_message}")
                
        except Exception as e:
            print(f"✗ Lỗi: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Testing Qwen 7B với prompt đơn giản...")
    asyncio.run(test_qwen_simple())
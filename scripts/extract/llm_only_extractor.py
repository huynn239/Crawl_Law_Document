#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM Only Extractor - Hệ thống B chỉ dùng Crawl4AI + Gemini"""
import sys
import os
from typing import Dict
from pathlib import Path

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from crawl4ai import AsyncWebCrawler, LLMConfig
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    from pydantic import BaseModel, Field
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

if CRAWL4AI_AVAILABLE:
    class Formula(BaseModel):
        name: str = Field(description="Tên công thức")
        formula: str = Field(description="Công thức tính toán")
        description: str = Field(description="Mô tả công thức")
        context: str = Field(description="Ngữ cảnh xung quanh công thức")
        confidence: float = Field(description="Độ tin cậy", default=0.9)
        type: str = Field(description="Loại công thức", default="llm_detected")

    class Parameter(BaseModel):
        name: str = Field(description="Tên tham số")
        value: str = Field(description="Giá trị tham số")
        type: str = Field(description="Loại tham số")
        confidence: float = Field(description="Độ tin cậy", default=0.9)

    class FormulaParameterExtraction(BaseModel):
        formulas: list[Formula] = Field(description="Danh sách công thức thật (có phép toán)")
        parameters: list[Parameter] = Field(description="Danh sách tham số (định nghĩa giá trị)")
        total_formulas: int = Field(description="Tổng số công thức")
        total_parameters: int = Field(description="Tổng số tham số")

class LLMOnlyExtractor:
    def __init__(self):
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("Crawl4AI not available. Install with: pip install crawl4ai")
    
    async def extract_from_url(self, url: str) -> Dict:
        """Trích xuất chỉ bằng Crawl4AI + Gemini, không dùng Regex"""
        
        # Prompt tối ưu cho Gemini
        extraction_prompt = """
        Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam. Hãy tách riêng CÔNG THỨC và THAM SỐ:

        🧮 CÔNG THỨC (formulas): Chỉ những biểu thức có PHÉP TOÁN thật sự
        - Có dấu =, ×, /, +, -, ngoặc đơn ()
        - Ví dụ: "Tiền lương = (A × B) / C"
        - Ví dụ: "Phụ cấp = 25% × lương cơ bản"

        📊 THAM SỐ (parameters): Định nghĩa giá trị cố định
        - Chỉ có dấu : hoặc = với số cụ thể
        - Ví dụ: "Mức lương cơ bản: 1.800.000 đồng"
        - Ví dụ: "Thuế suất: 10%"

        QUAN TRỌNG: Phân biệt rõ ràng giữa công thức tính toán và tham số định nghĩa.
        """
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            # Cấu hình LLM - Gemini 2.5 Pro
            from config import LLM_PROVIDER, LLM_API_KEY, OPENAI_API_KEY
            
            if LLM_API_KEY and "gemini" in LLM_PROVIDER.lower():
                llm_config = LLMConfig(
                    provider=LLM_PROVIDER,
                    api_token=LLM_API_KEY
                )
                print(f"🤖 Using {LLM_PROVIDER}")
            elif OPENAI_API_KEY:
                llm_config = LLMConfig(
                    provider="openai/gpt-4o-mini",
                    api_token=OPENAI_API_KEY
                )
                print("🤖 Using OpenAI GPT-4o-mini (fallback)")
            else:
                raise ValueError("No LLM API key found. Set GOOGLE_API_KEY or OPENAI_API_KEY")
            
            extraction_strategy = LLMExtractionStrategy(
                llm_config=llm_config,
                schema=FormulaParameterExtraction.model_json_schema(),
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
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    """,
                    wait_for="networkidle"
                )
                
                if result.success and result.extracted_content:
                    extracted_data = result.extracted_content
                    
                    # Handle string response
                    if isinstance(extracted_data, str):
                        import json
                        try:
                            extracted_data = json.loads(extracted_data)
                        except:
                            extracted_data = {"formulas": [], "parameters": [], "total_formulas": 0, "total_parameters": 0}
                    
                    return {
                        'url': url,
                        'formulas': extracted_data.get('formulas', []),
                        'parameters': extracted_data.get('parameters', []),
                        'total_formulas': extracted_data.get('total_formulas', 0),
                        'total_parameters': extracted_data.get('total_parameters', 0),
                        'content_length': len(result.cleaned_html),
                        'extraction_method': 'llm_only_system_b_crawl4ai_gemini'
                    }
                else:
                    return {
                        'url': url,
                        'error': result.error_message if hasattr(result, 'error_message') else 'Unknown error',
                        'formulas': [],
                        'parameters': [],
                        'total_formulas': 0,
                        'total_parameters': 0,
                        'extraction_method': 'llm_only_system_b_failed'
                    }
                    
            except Exception as e:
                return {
                    'url': url,
                    'error': str(e),
                    'formulas': [],
                    'parameters': [],
                    'total_formulas': 0,
                    'total_parameters': 0,
                    'extraction_method': 'llm_only_system_b_failed'
                }
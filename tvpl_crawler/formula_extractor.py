# -*- coding: utf-8 -*-
"""Extract công thức tính toán từ tab nội dung (tab1) - Phiên bản cải tiến"""
import re
import asyncio
from typing import Dict, List, Optional
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

    class FormulaExtraction(BaseModel):
        formulas: List[Formula] = Field(description="Danh sách các công thức tìm thấy")
        total_formulas: int = Field(description="Tổng số công thức")

# Import improved extractor - commented out to avoid import error
# from pathlib import Path
# import sys
# sys.path.append(str(Path(__file__).parent.parent))
# from final_formula_extractor import FinalFormulaExtractor

async def extract_formulas_with_crawl4ai(url: str, cookies_path: Optional[str] = None) -> Dict:
    """Extract công thức từ tab nội dung bằng Crawl4AI + LLM hoặc fallback"""
    
    if not CRAWL4AI_AVAILABLE:
        # Fallback to enhanced simple extractor
        print("Crawl4AI not available, using enhanced simple extractor")
        extractor = EnhancedSimpleExtractor()
        
        # Use playwright to get content
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            context_options = {}
            if cookies_path and Path(cookies_path).exists():
                context_options["storage_state"] = cookies_path
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                result = await extractor.extract_from_page(page, url)
                return result
            finally:
                await browser.close()
        
        return {
            "url": url,
            "error": "Failed to extract with fallback method",
            "formulas": [],
            "total_formulas": 0
        }
    
    # Prompt tối ưu cho Qwen 7B - đơn giản và rõ ràng
    extraction_prompt = """
    Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam. Hãy tìm và trích xuất TẤT CẢ các công thức tính toán trong văn bản.
    
    NHIỆM VỤ: Tìm các công thức có dạng:
    - Lương = [số tiền] đồng
    - Phụ cấp = [tỷ lệ]% × [cơ sở tính]
    - Thuế = [thu nhập] × [tỷ lệ]%
    - Tiền phạt = [số tiền] + [tỷ lệ]% × [giá trị]
    - Mức [tên] = [số tiền] đồng
    - Tỷ lệ [tên]: [số]%
    
    VÍ DỤ MONG MUỐN:
    - "Mức lương cơ bản = 1.800.000 đồng/tháng"
    - "Phụ cấp trách nhiệm = 20% × lương cơ bản"
    - "Thuế thu nhập cá nhân = thu nhập × 10%"
    
    KHÔNG lấy:
    - Số điều, khoản (Điều 1, Khoản 2)
    - Ngày tháng (23/9/2025)
    - Số văn bản (21/2025/TT-BGĐĐT)
    
    Trả về JSON với format:
    {
      "formulas": [
        {
          "name": "Tên công thức",
          "formula": "Công thức đầy đủ",
          "description": "Mô tả ngắn gọn",
          "context": "Ngữ cảnh trong văn bản"
        }
      ],
      "total_formulas": số_lượng
    }
    """
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Cấu hình LLM - tự động chọn giữa OpenAI và Ollama
        import os
        if os.getenv("OPENAI_API_KEY"):
            llm_config = LLMConfig(
                provider="openai/gpt-4o-mini",  # Rẻ và nhanh
                api_token=None  # Đọc từ env var
            )
            print("Using OpenAI GPT-4o-mini")
        else:
            llm_config = LLMConfig(
                provider="ollama/qwen:7b",  # Qwen 7B model - tốt cho tiếng Việt
                api_token=None,
                base_url="http://localhost:8080"
            )
            print("Using Ollama qwen:7b on port 8080")
        
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=FormulaExtraction.model_json_schema(),
            extraction_type="schema",
            instruction=extraction_prompt
        )
        
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
            
            # Handle None or invalid LLM response
            if extracted_data is None or not extracted_data:
                print("LLM returned None, using regex fallback")
                formulas = extract_formulas_regex_fallback(result.cleaned_html)
                extracted_data = {"formulas": formulas, "total_formulas": len(formulas)}
            elif isinstance(extracted_data, str):
                import json
                try:
                    extracted_data = json.loads(extracted_data)
                except:
                    print("Failed to parse LLM JSON, using regex fallback")
                    formulas = extract_formulas_regex_fallback(result.cleaned_html)
                    extracted_data = {"formulas": formulas, "total_formulas": len(formulas)}
            
            return {
                "url": url,
                "tab1_content_length": len(result.cleaned_html),
                "formulas": extracted_data.get("formulas", []),
                "total_formulas": extracted_data.get("total_formulas", 0),
                "extraction_method": "crawl4ai_llm_with_fallback"
            }
        else:
            return {
                "url": url,
                "error": result.error_message,
                "formulas": [],
                "total_formulas": 0
            }

def extract_formulas_regex_fallback(html_content: str) -> List[Dict]:
    """Fallback regex extraction nếu LLM không hoạt động"""
    formulas = []
    
    # Clean HTML first - remove tags but keep text
    import re
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Patterns cho các loại công thức thực sự - chính xác hơn
    patterns = [
        # Công thức có dấu = với số tiền cụ thể
        r'([A-Za-zÀ-ỹ\s]{5,50})\s*=\s*([\d.,]+(?:\s*(?:đồng|VNĐ|%))?)(?:\s*/\s*[A-Za-zÀ-ỹ]+)?',
        
        # Công thức tính % rõ ràng
        r'([\d.,]+)\s*%\s*(?:của|×|\*)\s*([\d.,]+(?:\s*(?:đồng|VNĐ))?)',
        
        # Công thức có phép tính + - × /
        r'([A-Za-zÀ-ỹ\s]{5,40})\s*=\s*([\d.,]+)\s*([+\-×*/])\s*([\d.,]+)(?:\s*(?:đồng|VNĐ|%))?',
        
        # Mức/Tỷ lệ với số cụ thể
        r'((?:mức|tỷ\s*lệ)\s*[^:]{5,40}):\s*([\d.,]+\s*(?:%|đồng|VNĐ))',
        
        # Công thức tính lương/phụ cấp
        r'((?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí)\s*[^=]{5,40})\s*=\s*([\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))?)',
        
        # Công thức có từ "tính" hoặc "bằng"
        r'(tính|bằng)\s*([^.]{10,80}(?:[\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))))',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            formula_text = match.group(0).strip()
            
            # Filter out HTML artifacts and invalid formulas
            if (len(formula_text) > 15 and len(formula_text) < 300 and
                not any(x in formula_text.lower() for x in ['<', '>', 'href', 'class', 'style', 'div', 'span', 'aspx', 'listidlaw', 'javascript', 'function', 'var ', 'document']) and
                any(char.isdigit() for char in formula_text) and
                ('=' in formula_text or '%' in formula_text or any(op in formula_text for op in ['+', '-', '×', '*', '/'])) and
                any(word in formula_text.lower() for word in ['lương', 'phụ cấp', 'thuế', 'phí', 'tiền', 'mức', 'tỷ lệ', 'tính', 'bằng', 'đồng', 'vnd', '%'])):
                
                formulas.append({
                    "name": f"Công thức {len(formulas) + 1}",
                    "formula": formula_text,
                    "description": f"Công thức tính toán (pattern {i})",
                    "context": formula_text[:150] + "..." if len(formula_text) > 150 else formula_text
                })
    
    # Remove duplicates
    seen = set()
    unique_formulas = []
    for f in formulas:
        if f['formula'] not in seen:
            seen.add(f['formula'])
            unique_formulas.append(f)
    
    return unique_formulas[:20]  # Limit to top 20 formulas

# Import enhanced simple extractor - commented out to avoid import error
# from pathlib import Path
# import sys
# sys.path.append(str(Path(__file__).parent.parent))
# from enhanced_simple_extractor import EnhancedSimpleExtractor

async def extract_tab1_content_simple(page, url: str) -> Dict:
    """Extract tab1 content với độ chính xác cao cho lương"""
    try:
        # Sử dụng enhanced simple extractor
        extractor = EnhancedSimpleExtractor()
        result = await extractor.extract_from_page(page, url)
        
        # Convert to expected format
        return {
            "url": url,
            "tab1_content_length": result.get("content_length", 0),
            "formulas": result.get("formulas", []),
            "total_formulas": result.get("total_formulas", 0),
            "extraction_method": "enhanced_simple"
        }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "formulas": [],
            "total_formulas": 0
        }
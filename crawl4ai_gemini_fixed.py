#!/usr/bin/env python3
"""
Crawl4AI + Gemini - 3 Layer Strategy (Improved Version)
Layer 1: Regex
Layer 2: LLM (Gemini)
Layer 3: Manual Review
"""

import os
import re
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class Crawl4AIGeminiExtractor:
    def __init__(self):
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai not installed")
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        
        # --- (CẢI TIẾN) ---
        # Dùng 1.5 Flash cho tốc độ và chi phí tối ưu
        # Bật chế độ JSON mode cho Gemini
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.gemini_json_config = genai.GenerationConfig(
            response_mime_type="application/json"
        )
        
        # --- LAYER 1: REGEX PATTERNS ---
        self.formula_patterns = [
            re.compile(r"(Tiền lương 01 tiết dạy[^=]{0,50}=\s*[^.]{20,300})", re.IGNORECASE),
            re.compile(r"(Số tiết dạy thêm[^=]{5,50}=\s*[^.]{20,200})", re.IGNORECASE),
            re.compile(r"(Định mức tiết dạy/năm học[^=]{5,50}=\s*[^.]{20,200})", re.IGNORECASE),
            re.compile(r"((?:Tổng|Số|Mức|Tỷ lệ|Tiền lương)[^=]{5,100})\s*=\s*([^.]{15,200})", re.IGNORECASE)
        ]

    # --- HÀM CỦA LAYER 1 ---
    def extract_with_regex(self, content: str) -> tuple:
        """Thử bóc tách công thức bằng Regex (nhanh, rẻ)"""
        print("[LAYER 1] Đang chạy Regex...")
        formulas = []
        
        # --- DANH SÁCH TỪ KHÓA RÁC ---
        junk_keywords = [
            'http:', 'https://', '.aspx', '.html', '.vn', 
            'thuvienphapluat', 'utm_', 'cdn.', 'img', 'Sign in'
        ]
        
        for pattern in self.formula_patterns:
            for match in pattern.finditer(content):
                formula_text = match.group(0).strip()
                formula_text_lower = formula_text.lower()
                
                # --- BỘ LỌC CHẤT LƯỢNG ---
                if len(formula_text) < 20 or re.search(r'\b\d{2,4}/\d{4}\b', formula_text):
                    continue
                if any(junk in formula_text_lower for junk in junk_keywords):
                    continue
                if not any(op in formula_text for op in ['=', '+', '-', '*', '×', '/']):
                    continue
                
                formulas.append({
                    "name": formula_text[:70] + "...",
                    "formula": formula_text,
                    "type": "regex_detected",
                    "confidence": 0.9,
                    "extraction_method": "layer_1_regex"
                })
        
        # --- (ĐÃ SỬA) CHUYỂN LOGIC TÍNH TOÁN XUỐNG ĐÂY ---
        
        # --- TÍNH CONFIDENCE SCORE ---
        quality_indicators = [
            'Điều 4', 'Điều 5', 'Điều 6',
            'Tiền lương', 'tiết dạy', 'định mức',
            '52 tuần', '1760 giờ', '44 tuần'
        ]
        
        quality_score = sum(1 for indicator in quality_indicators if indicator.lower() in content.lower())
        
        # CONFIDENCE SCORE (0.0 - 1.0)
        # Giờ len(formulas) đã có giá trị
        quantity_score = min(1.0, len(formulas) / 10.0) 
        quality_ratio = quality_score / len(quality_indicators)
        
        confidence_score = (quantity_score * 0.6) + (quality_ratio * 0.4)
        
        # NGƯỠNG TIN CẬY
        CONFIDENCE_THRESHOLD = 0.75 # Dưới 0.75 thì chuyển Layer 2
        
        print(f"[LAYER 1] Regex tìm thấy: {len(formulas)} công thức.")
        print(f"[LAYER 1] Confidence Score: {confidence_score:.2f} (Ngưỡng: {CONFIDENCE_THRESHOLD})")
        
        return formulas, confidence_score, CONFIDENCE_THRESHOLD

    # --- HÀM CỦA LAYER 2 ---
    async def extract_with_gemini(self, content: str) -> dict:
        """Nếu Regex thất bại, dùng LLM (Gemini)"""
        print("[LAYER 2] Đang chạy Gemini...")
        prompt = f"""
        Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam. 
        Tôi đã chạy Regex nhưng không tìm thấy công thức nào.
        Hãy phân tích kỹ văn bản sau và trích xuất BẤT KỲ công thức nào bạn tìm thấy.

        VĂN BẢN:
        {content[:20000]}

        YÊU CẦU: Trả về CHỈ JSON, không giải thích gì thêm, theo định dạng:
        {{
          "formulas": [
            {{
              "name": "Tên công thức chi tiết",
              "formula": "Công thức toán học chính xác từ văn bản",
              "variables": ["danh sách biến số"],
              "article": "Điều X"
            }}
          ],
          "parameters": [
            {{ "name": "Tên tham số", "value": "giá trị", "unit": "đơn vị" }}
          ]
        }}
        """
        try:
            # --- (CẢI TIẾN) ---
            # Sử dụng async và bật JSON mode
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.gemini_json_config
            )
            result_text = response.text.strip()
            
            print(f"[DEBUG] Gemini response: {result_text[:200]}...")
            
            # Không cần dọn dẹp "```json" nữa
            result = json.loads(result_text)
            result["extraction_method"] = "layer_2_gemini"
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"Lỗi Gemini: {error_msg}")
            return {"formulas": [], "parameters": [], "error": error_msg, "extraction_method": "layer_2_gemini_failed"}

    # --- HÀM ĐIỀU PHỐI 3 LỚP ---
    async def crawl_and_extract_3_layer(self, url: str) -> dict:
        
        # --- CRAWL (Bước 0) ---
        print(f"Đang crawl URL: {url}")
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                crawl_result = await crawler.arun(url=url, word_count_threshold=100)
            
            content = crawl_result.markdown or crawl_result.cleaned_html
            if not content:
                return {"error": "No content extracted", "url": url, "extraction_method": "failed_crawl"}
        
        except Exception as e:
            return {"error": f"Crawl4AI failed: {e}", "url": url, "extraction_method": "failed_crawl"}

        # --- LAYER 1: REGEX ---
        regex_formulas, confidence_score, threshold = self.extract_with_regex(content)
        
        # --- (ĐÃ SỬA) BỎ CÁC BIẾN KHÔNG DÙNG ---
        
        # --- QUYẾT ĐỊNH TIN CẬY DỰA TRÊN CONFIDENCE SCORE ---
        if confidence_score >= threshold:
            # Regex thành công! Tin cậy hoàn toàn
            print(f"Hoàn tất: Layer 1 tin cậy (Score: {confidence_score:.2f})")
            return {
                "formulas": regex_formulas,
                "parameters": [],
                "total_formulas": len(regex_formulas),
                "total_parameters": 0,
                "extraction_method": "layer_1_regex_confident",
                "confidence_score": confidence_score,
                "confidence_threshold": threshold,
                "url": url,
                "content_length": len(content)
            }
        
        # Không tin cậy - chuyển Layer 2
        print(f"Layer 1 không tin cậy (Score: {confidence_score:.2f} < {threshold}). Chuyển Layer 2.")
        reason = f"Confidence score thấp: {confidence_score:.2f}"

        # --- LAYER 2: LLM (Vì Layer 1 không tin cậy) ---
        llm_result = await self.extract_with_gemini(content)
        
        llm_result.update({
            "url": url,
            "content_length": len(content),
            "total_formulas": len(llm_result.get('formulas', [])),
            "total_parameters": len(llm_result.get('parameters', [])),
            "layer1_results": len(regex_formulas),
            "layer1_confidence": confidence_score,
            "fallback_reason": reason
        })
        
        # --- LAYER 3: MANUAL ---
        if llm_result.get('error'):
            print(f"Hoàn tất: Layer 2 (LLM) lỗi: {llm_result['error']}")
            llm_result["extraction_method"] = "layer_3_manual_needed"
        elif not llm_result.get('formulas'):
            print("Hoàn tất: Layer 2 (LLM) không tìm thấy công thức.")
            llm_result["extraction_method"] = "layer_3_manual_needed"
        else:
            print(f"Hoàn tất: Layer 2 (LLM) thành công với {len(llm_result['formulas'])} công thức.")

        return llm_result

async def test_3_layer_strategy():
    """Test chiến lược 3 lớp"""
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    extractor = Crawl4AIGeminiExtractor()
    result = await extractor.crawl_and_extract_3_layer(url)
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/crawl4ai_gemini_3_layer_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n--- KẾT QUẢ CUỐI CÙNG ---")
    print(f"Method: {result.get('extraction_method', 'unknown')}")
    print(f"Formulas: {result.get('total_formulas', 0)}")
    print(f"Parameters: {result.get('total_parameters', 0)}")
    print(f"File: {output_file}")
    if result.get('error'):
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_3_layer_strategy())
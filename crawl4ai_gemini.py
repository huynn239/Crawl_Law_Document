import re # Đừng quên import re

class Crawl4AIGeminiExtractor:
    def __init__(self):
        # ... (Giữ nguyên code init của bạn)
        
        # --- LAYER 1: REGEX PATTERNS ---
        # (Lấy lại các pattern tốt nhất từ file UltimateExtractor của bạn)
        self.formula_patterns = [
            re.compile(r"(Tiền lương 01 tiết dạy[^=]{0,50}=\s*[^.]{20,300})", re.IGNORECASE),
            re.compile(r"(Số tiết dạy thêm[^=]{5,50}=\s*[^.]{20,200})", re.IGNORECASE),
            # ... (thêm các pattern regex khác) ...
        ]

    # --- HÀM CỦA LAYER 1 ---
    def extract_with_regex(self, content: str) -> list:
        print("[Layer 1] Đang chạy Regex...")
        formulas = []
        for pattern in self.formula_patterns:
            for match in pattern.finditer(content):
                formulas.append({
                    "name": match.group(0)[:50] + "...",
                    "formula": match.group(0),
                    "type": "regex_detected",
                    "confidence": 0.9,
                    "context": "N/A (Regex)",
                    "extraction_method": "layer_1_regex"
                })
        return formulas

    # --- HÀM CỦA LAYER 2 ---
    async def extract_with_gemini(self, content: str) -> dict:
        print("[Layer 2] Đang chạy Gemini...")
        prompt = f"""
        Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam. 
        Regex đã thất bại trong việc tìm công thức. 
        Hãy phân tích kỹ văn bản sau và trích xuất BẤT KỲ công thức nào bạn tìm thấy.

        VĂN BẢN:
        {content[:15000]}

        YÊU CẦU: Trả về JSON theo định dạng sau (chỉ trả về JSON, không giải thích gì thêm):
        {{
          "formulas": [
            {{
              "name": "Tên công thức",
              "formula": "Công thức toán học",
              "variables": ["biến số 1", "biến số 2"],
              "article": "Điều X"
            }}
          ],
          "parameters": [
            {{ "name": "Tham số", "value": "giá trị", "unit": "đơn vị" }}
          ]
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # (Giữ nguyên code clean JSON của bạn)
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text)
            result["extraction_method"] = "layer_2_gemini"
            return result
            
        except Exception as e:
            print(f"Lỗi Gemini: {e}")
            return {"formulas": [], "parameters": [], "error": str(e)}

    # --- HÀM ĐIỀU PHỐI 3 LỚP ---
    async def crawl_and_extract_3_layer(self, url: str) -> dict:
        
        # --- CRAWL (Bước 0) ---
        print(f"Đang crawl URL: {url}")
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                crawl_result = await crawler.arun(url=url)
            
            content = crawl_result.markdown or crawl_result.cleaned_html
            if not content or len(content) < 100:
                return {"error": "No content extracted", "url": url, "extraction_method": "failed_crawl"}
        
        except Exception as e:
            return {"error": f"Crawl4AI failed: {e}", "url": url, "extraction_method": "failed_crawl"}

        # --- LAYER 1: REGEX ---
        regex_formulas = self.extract_with_regex(content)
        
        if regex_formulas:
            # Regex thành công! Trả về kết quả và tiết kiệm chi phí
            print(f"Layer 1 (Regex) thành công: Tìm thấy {len(regex_formulas)} công thức.")
            return {
                "formulas": regex_formulas,
                "parameters": [], # (Bạn có thể thêm regex cho param)
                "total_formulas": len(regex_formulas),
                "total_parameters": 0,
                "extraction_method": "layer_1_regex",
                "url": url,
                "content_length": len(content)
            }

        # --- LAYER 2: LLM (Vì Layer 1 thất bại) ---
        print("Layer 1 (Regex) thất bại. Chuyển sang Layer 2 (LLM)...")
        llm_result = await self.extract_with_gemini(content)
        
        llm_result.update({
            "url": url,
            "content_length": len(content),
            "total_formulas": len(llm_result.get('formulas', [])),
            "total_parameters": len(llm_result.get('parameters', []))
        })
        
        # --- LAYER 3: MANUAL ---
        if not llm_result.get('formulas'):
            print("Layer 2 (LLM) cũng thất bại. Cần xem xét thủ công.")
            llm_result["extraction_method"] = "layer_3_manual_needed"

        return llm_result

async def test_crawl4ai_gemini():
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    extractor = Crawl4AIGeminiExtractor()
    # Gọi hàm điều phối 3 lớp mới
    result = await extractor.crawl_and_extract_3_layer(url)
    
    # ... (Giữ nguyên code lưu file và in kết quả của bạn) ...
    os.makedirs('data', exist_ok=True)
    output_file = 'data/crawl4ai_gemini_3_layer_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n--- HOÀN TẤT ---")
    print(f"Method: {result.get('extraction_method', 'unknown')}")
    print(f"Formulas: {result.get('total_formulas', 0)}")
    print(f"File: {output_file}")
    if result.get('error'):
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_crawl4ai_gemini())
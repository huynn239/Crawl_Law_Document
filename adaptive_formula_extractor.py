#!/usr/bin/env python3
"""
Adaptive Formula Extractor - Tự động thích ứng với nhiều loại văn bản pháp luật
"""

import re
from typing import List, Dict, Any
from ultimate_formula_extractor import UltimateFormulaExtractor

class AdaptiveFormulaExtractor(UltimateFormulaExtractor):
    def __init__(self, openai_api_key=None):
        super().__init__(openai_api_key)
        
        # Thêm patterns cho các lĩnh vực khác
        self.domain_patterns = {
            'education': [
                (r'(Tiền lương[^=]{5,50}=\s*[^.]{20,200})', 'salary_calc', 0.95),
                (r'(Số tiết[^=]{5,50}=\s*[^.]{20,200})', 'teaching_hours', 0.95),
                (r'(Định mức[^=]{5,50}=\s*[^.]{20,200})', 'quota_calc', 0.9),
            ],
            'tax': [
                (r'(Thuế[^=]{5,50}=\s*[^.]{20,200})', 'tax_calc', 0.95),
                (r'(Mức thuế[^=]{5,50}=\s*[^.]{15,150})', 'tax_rate', 0.9),
                (r'(\d+%\s*[^.]{10,100})', 'percentage', 0.8),
            ],
            'labor': [
                (r'(Lương[^=]{5,50}=\s*[^.]{20,200})', 'wage_calc', 0.95),
                (r'(Phụ cấp[^=]{5,50}=\s*[^.]{15,150})', 'allowance', 0.9),
                (r'(Bảo hiểm[^=]{5,50}=\s*[^.]{15,150})', 'insurance', 0.9),
            ],
            'finance': [
                (r'(Lãi suất[^=]{5,50}=\s*[^.]{15,150})', 'interest_rate', 0.9),
                (r'(Phí[^=]{5,50}=\s*[^.]{15,150})', 'fee_calc', 0.85),
                (r'(Tỷ lệ[^=]{5,50}=\s*[^.]{15,150})', 'ratio_calc', 0.85),
            ]
        }
    
    def detect_document_domain(self, text: str) -> str:
        """Tự động phát hiện lĩnh vực của văn bản"""
        text_lower = text.lower()
        
        domain_keywords = {
            'education': ['giáo dục', 'nhà giáo', 'giáo viên', 'tiết dạy', 'học sinh'],
            'tax': ['thuế', 'khai thuế', 'thu nhập', 'tncn', 'gtgt'],
            'labor': ['lao động', 'người lao động', 'hợp đồng lao động', 'bảo hiểm xã hội'],
            'finance': ['ngân hàng', 'tín dụng', 'lãi suất', 'tiền tệ', 'tài chính']
        }
        
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[domain] = score
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'general'
    
    def get_adaptive_patterns(self, domain: str) -> List:
        """Lấy patterns phù hợp với lĩnh vực"""
        base_patterns = self.formula_patterns.copy()
        
        if domain in self.domain_patterns:
            # Thêm patterns chuyên biệt cho lĩnh vực
            domain_specific = self.domain_patterns[domain]
            base_patterns.extend(domain_specific)
        
        return base_patterns
    
    async def extract_formulas(self, url: str = None, text: str = None) -> Dict[str, Any]:
        """Extract với adaptive patterns"""
        if url and not text:
            text = await self.extract_from_url_with_crawl4ai(url)
            
        if not text:
            return {
                'formulas': [], 'parameters': [], 'total_formulas': 0, 
                'total_parameters': 0, 'extraction_method': 'failed_no_content',
                'error': 'No content available'
            }
        
        # Phát hiện lĩnh vực
        domain = self.detect_document_domain(text)
        
        # Cập nhật patterns theo lĩnh vực
        original_patterns = self.formula_patterns
        self.formula_patterns = self.get_adaptive_patterns(domain)
        
        # Extract với patterns thích ứng
        candidates = self.extract_formula_candidates(text)
        formulas = self.validate_and_clean_formulas(candidates)
        parameters = self.extract_parameters(text)
        unique_formulas = self.deduplicate_formulas(formulas)
        unique_formulas.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Khôi phục patterns gốc
        self.formula_patterns = original_patterns
        
        return {
            'formulas': unique_formulas,
            'parameters': parameters,
            'total_formulas': len(unique_formulas),
            'total_parameters': len(parameters),
            'extraction_method': f'adaptive_{domain}',
            'detected_domain': domain,
            'url': url,
            'content_length': len(text)
        }

# Test với nhiều loại văn bản
async def test_adaptive():
    extractor = AdaptiveFormulaExtractor()
    
    # Test văn bản giáo dục
    education_text = """
    Tiền lương 01 tiết dạy = Tổng lương 12 tháng × Số tuần / Định mức tiết dạy
    Số tiết dạy thêm = Tổng tiết thực tế - Định mức tiết dạy
    """
    
    # Test văn bản thuế
    tax_text = """
    Thuế thu nhập cá nhân = Thu nhập chịu thuế × Thuế suất
    Mức thuế suất = 10% đối với thu nhập dưới 5 triệu đồng
    """
    
    results = []
    for text, name in [(education_text, 'education'), (tax_text, 'tax')]:
        result = await extractor.extract_formulas(text=text)
        results.append({
            'document_type': name,
            'detected_domain': result['detected_domain'],
            'formulas_found': result['total_formulas'],
            'extraction_method': result['extraction_method']
        })
    
    return results

if __name__ == "__main__":
    import asyncio
    results = asyncio.run(test_adaptive())
    for r in results:
        print(f"Document: {r['document_type']}")
        print(f"Detected: {r['detected_domain']}")
        print(f"Formulas: {r['formulas_found']}")
        print(f"Method: {r['extraction_method']}")
        print()
#!/usr/bin/env python3
"""
Ultimate Formula Extractor - Combines Crawl4AI + Enhanced Regex + LLM + Validation
Best accuracy for Vietnamese legal documents
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

@dataclass
class FormulaMatch:
    text: str
    context: str
    pattern_type: str
    confidence: float
    is_formula: bool = True

class UltimateFormulaExtractor:
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        
        # Enhanced patterns for Vietnamese legal formulas
        self.formula_patterns = [
            # Salary calculation formulas (most important)
            (r'(Tiền lương\s+(?:01|1)\s+tiết\s+dạy[^=]{0,50}=\s*[^.]{20,300})', 'salary_per_lesson', 0.98),
            (r'(Tiền lương[^=]{5,50}=\s*[^.]{20,200})', 'salary_calc', 0.95),
            
            # Table-style formulas with | separators
            (r'(Tiền lương[^|]{0,50}\|[^|]{0,30}=[^|]{0,30}\|[^.]{20,300})', 'table_formula', 0.92),
            (r'([^|]{10,80}\|[^|]{5,30}=[^|]{5,30}\|[^|]{10,100}\|[^|]{5,50}×[^.]{10,200})', 'complex_table', 0.9),
            
            # Complete equations with equals
            (r'([^.]{10,100})\s*=\s*([^.]{15,150}(?:[+\-×*/]\s*[^.]{5,100})*)', 'complete_equation', 0.95),
            
            # Teaching hours formulas
            (r'(Số tiết[^=]{5,50}=\s*[^.]{20,200})', 'teaching_hours', 0.95),
            (r'(Định mức tiết dạy[^=]{5,50}=\s*[^.]{20,200})', 'quota_calc', 0.9),
            
            # Mathematical operations
            (r'([^.]{15,80})\s*[×x*]\s*([^.]{15,80})', 'multiplication', 0.9),
            (r'([^.]{15,80})\s*/\s*([^.]{15,80})', 'division', 0.9),
            
            # Complex calculations with parentheses
            (r'([^.]{10,60})\s*=\s*\([^)]{10,100}\)\s*[-+×*/]\s*\([^)]{10,100}\)', 'complex_calc', 0.95),
            
            # Rate and amount calculations
            (r'(Mức[^=]{5,50}=\s*[^.]{15,150})', 'rate_calc', 0.85),
        ]
        
        # Parameter patterns (non-formulas)
        self.parameter_patterns = [
            (r'(không\s+(?:quá|dưới|trên)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,50}))', 'limit', 0.9),
            (r'(tối\s+(?:đa|thiểu)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,50}))', 'limit', 0.9),
            (r'((?:bằng|là)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,50}))', 'fixed_value', 0.8),
        ]

    async def extract_from_url_with_crawl4ai(self, url: str) -> str:
        """Extract content using Crawl4AI with LLM instruction"""
        if not CRAWL4AI_AVAILABLE:
            return ""
            
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    extraction_strategy={
                        "type": "llm",
                        "instruction": """
                        Extract all mathematical formulas and calculations from this Vietnamese legal document.
                        Focus on salary calculations, teaching hours, quotas, and any mathematical expressions.
                        Include the complete text context around each formula.
                        """
                    } if self.openai_api_key else None,
                    bypass_cache=True
                )
                
                return result.extracted_content or result.markdown or ""
                
        except Exception:
            return ""

    def extract_formula_candidates(self, text: str) -> List[FormulaMatch]:
        """Extract formula candidates using enhanced regex"""
        candidates = []
        
        for pattern, pattern_type, base_confidence in self.formula_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                full_match = match.group(0).strip()
                
                # Quality filters
                if len(full_match) < 20:
                    continue
                    
                # Skip document numbers
                if re.search(r'\b\d{2,4}/\d{4}\b', full_match):
                    continue
                    
                # Get context
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 150)
                context = text[start:end]
                
                # Boost confidence for education terms
                confidence = base_confidence
                education_terms = ['tiết', 'lương', 'định mức', 'giáo viên', 'học', 'mức']
                if any(term in full_match.lower() for term in education_terms):
                    confidence = min(1.0, confidence + 0.05)
                
                candidates.append(FormulaMatch(
                    text=full_match,
                    context=context,
                    pattern_type=pattern_type,
                    confidence=confidence
                ))
        
        return candidates

    def extract_parameters(self, text: str) -> List[Dict[str, Any]]:
        """Extract parameters (non-formula values)"""
        parameters = []
        
        for pattern, param_type, confidence in self.parameter_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                full_match = match.group(0).strip()
                
                # Extract value if available
                value = ""
                if match.lastindex >= 2:
                    value = match.group(2)
                
                parameters.append({
                    'name': match.group(1).strip(),
                    'value': value,
                    'full_text': full_match,
                    'type': param_type,
                    'confidence': confidence
                })
        
        return parameters

    def validate_and_clean_formulas(self, candidates: List[FormulaMatch]) -> List[Dict[str, Any]]:
        """Validate and clean formula candidates"""
        validated = []
        
        for candidate in candidates:
            # Must contain mathematical operators
            if not any(op in candidate.text for op in ['=', '×', 'x', '*', '/', '+', '-', '(', ')']):
                continue
                
            # Clean up the formula text
            cleaned_text = self._clean_formula_text(candidate.text)
            
            if len(cleaned_text) < 15:
                continue
                
            validated.append({
                'name': cleaned_text[:60] + '...' if len(cleaned_text) > 60 else cleaned_text,
                'formula': cleaned_text,
                'type': candidate.pattern_type,
                'confidence': candidate.confidence,
                'context': candidate.context[:200],
                'extraction_method': 'ultimate_validated'
            })
        
        return validated

    def _clean_formula_text(self, text: str) -> str:
        """Clean and normalize formula text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove trailing numbers/punctuation that aren't part of formula
        text = re.sub(r'\s*[;,]\s*\d+\s*$', '', text)
        
        # Normalize multiplication symbols
        text = re.sub(r'\s*[×x]\s*', ' × ', text)
        
        return text

    def deduplicate_formulas(self, formulas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate formulas"""
        unique = []
        
        for formula in formulas:
            is_duplicate = False
            
            for existing in unique:
                # Check text similarity
                similarity = self._calculate_similarity(formula['formula'], existing['formula'])
                if similarity > 0.85:
                    # Keep the one with higher confidence
                    if formula['confidence'] > existing['confidence']:
                        unique.remove(existing)
                        break
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique.append(formula)
        
        return unique

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    async def extract_formulas(self, url: str = None, text: str = None) -> Dict[str, Any]:
        """Main extraction method"""
        if url and not text:
            # Extract from URL using Crawl4AI
            text = await self.extract_from_url_with_crawl4ai(url)
            
        if not text:
            return {
                'formulas': [],
                'parameters': [],
                'total_formulas': 0,
                'total_parameters': 0,
                'extraction_method': 'failed_no_content',
                'error': 'No content available'
            }
        
        # Extract candidates
        candidates = self.extract_formula_candidates(text)
        
        # Validate and clean
        formulas = self.validate_and_clean_formulas(candidates)
        
        # Extract parameters
        parameters = self.extract_parameters(text)
        
        # Remove duplicates
        unique_formulas = self.deduplicate_formulas(formulas)
        
        # Sort by confidence
        unique_formulas.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'formulas': unique_formulas,
            'parameters': parameters,
            'total_formulas': len(unique_formulas),
            'total_parameters': len(parameters),
            'extraction_method': 'ultimate_crawl4ai_regex',
            'url': url,
            'content_length': len(text)
        }


async def main():
    """Test the ultimate extractor"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize extractor
    openai_key = os.getenv('OPENAI_API_KEY')
    extractor = UltimateFormulaExtractor(openai_api_key=openai_key)
    
    # Test URL
    test_url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    # Test with sample text first
    sample_text = """
    Điều 3. Số tiết dạy thêm của nhà giáo được xác định như sau:
    
    1. Số tiết dạy thêm của nhà giáo/năm học = (Tổng số tiết dạy được tính thực tế/năm học) - (Định mức tiết dạy/năm học)
    
    2. Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm
    
    3. Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Số tiết dạy thêm không quá 200 tiết/năm học.
    
    5. Mức lương cơ bản tối thiểu là 1.800.000 đồng/tháng.
    """
    
    # Extract formulas
    result = await extractor.extract_formulas(url=test_url, text=sample_text)
    
    # Save results
    os.makedirs('data', exist_ok=True)
    output_file = 'data/ultimate_formulas_result.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("Ultimate extraction completed!")
    print(f"Found {result['total_formulas']} formulas, {result['total_parameters']} parameters")
    print(f"Results saved to: {output_file}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
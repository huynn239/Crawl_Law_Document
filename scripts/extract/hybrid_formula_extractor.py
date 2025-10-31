#!/usr/bin/env python3
"""
Hybrid Formula Extractor - Combines Crawl4AI + Regex + LLM for Vietnamese Legal Documents
Improved accuracy by using Crawl4AI for content extraction, regex for detection, and LLM for validation
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import openai
from loguru import logger

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI not available, using fallback content extraction")

@dataclass
class FormulaCandidate:
    text: str
    context: str
    pattern_type: str
    confidence: float
    start_pos: int
    end_pos: int

class HybridFormulaExtractor:
    def __init__(self, openai_api_key: Optional[str] = None, use_crawl4ai: bool = True):
        self.openai_api_key = openai_api_key
        self.use_crawl4ai = use_crawl4ai and CRAWL4AI_AVAILABLE
        
        if openai_api_key:
            openai.api_key = openai_api_key
        
        # Enhanced regex patterns for Vietnamese legal formulas
        self.formula_patterns = [
            # Mathematical equations with equals
            (r'([^.]{0,50})\s*=\s*([^.]{10,100}(?:[+\-×*/]\s*[^.]{5,50})*)', 'equation', 0.9),
            
            # Multiplication/division formulas
            (r'([^.]{10,80})\s*[×x*]\s*([^.]{10,80})', 'multiplication', 0.85),
            (r'([^.]{10,80})\s*/\s*([^.]{10,80})', 'division', 0.85),
            
            # Calculation formulas with parentheses
            (r'([^.]{0,50})\s*=\s*\([^)]+\)\s*[-+×*/]\s*\([^)]+\)', 'complex_calculation', 0.95),
            
            # Vietnamese specific patterns
            (r'(Số tiết[^=]{0,50}=\s*[^.]{20,150})', 'teaching_hours', 0.9),
            (r'(Tiền lương[^=]{0,50}=\s*[^.]{20,150})', 'salary_calculation', 0.9),
            (r'(Định mức[^=]{0,50}=\s*[^.]{20,150})', 'quota_calculation', 0.85),
            
            # Percentage and rate calculations
            (r'([^.]{10,80})\s*[×x*]\s*(\d+(?:[.,]\d+)?%)', 'percentage_calc', 0.8),
            
            # Range formulas (from X to Y)
            (r'(từ\s+[\d.,]+\s+đến\s+[\d.,]+[^.]{0,50})', 'range_formula', 0.7),
        ]
        
        # Parameter patterns (non-formula values)
        self.parameter_patterns = [
            (r'(không\s+(?:quá|dưới|trên)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,30}))', 'limit', 0.8),
            (r'(tối\s+(?:đa|thiểu)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,30}))', 'limit', 0.8),
            (r'((?:bằng|là)\s+(\d+(?:[.,]\d+)?)\s*([^.]{0,30}))', 'fixed_value', 0.7),
        ]

    def extract_candidates(self, text: str) -> List[FormulaCandidate]:
        """Extract formula candidates using regex patterns"""
        candidates = []
        
        # Extract formula candidates
        for pattern, pattern_type, base_confidence in self.formula_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                full_match = match.group(0).strip()
                if len(full_match) > 15:  # Filter out too short matches
                    # Get surrounding context
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end]
                    
                    candidates.append(FormulaCandidate(
                        text=full_match,
                        context=context,
                        pattern_type=pattern_type,
                        confidence=base_confidence,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        return candidates

    def validate_with_llm(self, candidates: List[FormulaCandidate]) -> List[Dict[str, Any]]:
        """Validate and refine candidates using LLM"""
        if not self.openai_api_key or not candidates:
            return self._fallback_validation(candidates)
        
        try:
            # Prepare candidates for LLM
            candidate_texts = []
            for i, candidate in enumerate(candidates):
                candidate_texts.append(f"{i+1}. {candidate.text}")
            
            prompt = f"""
Analyze these Vietnamese legal text excerpts and identify which are actual mathematical formulas vs parameters:

{chr(10).join(candidate_texts)}

For each item, respond with JSON format:
{{
  "item_number": 1,
  "is_formula": true/false,
  "formula_type": "calculation/multiplication/division/parameter",
  "cleaned_text": "cleaned version",
  "confidence": 0.0-1.0,
  "explanation": "brief reason"
}}

Rules:
- Formula: Must contain mathematical operations (=, ×, /, +, -, calculations)
- Parameter: Specific values, limits, percentages without calculations
- Clean up incomplete text fragments
- Focus on salary, teaching hours, quotas in Vietnamese education law
"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            return self._parse_llm_response(response.choices[0].message.content, candidates)
            
        except Exception as e:
            logger.warning(f"LLM validation failed: {e}, using fallback")
            return self._fallback_validation(candidates)

    def _parse_llm_response(self, response: str, candidates: List[FormulaCandidate]) -> List[Dict[str, Any]]:
        """Parse LLM response and combine with original candidates"""
        results = []
        
        try:
            # Extract JSON objects from response
            json_objects = re.findall(r'\{[^}]+\}', response)
            
            for i, json_str in enumerate(json_objects):
                if i >= len(candidates):
                    break
                    
                try:
                    llm_result = json.loads(json_str)
                    candidate = candidates[i]
                    
                    if llm_result.get('is_formula', False):
                        results.append({
                            'name': candidate.text[:50] + '...' if len(candidate.text) > 50 else candidate.text,
                            'formula': llm_result.get('cleaned_text', candidate.text),
                            'type': llm_result.get('formula_type', candidate.pattern_type),
                            'confidence': min(candidate.confidence, llm_result.get('confidence', 0.5)),
                            'context': candidate.context[:200],
                            'extraction_method': 'hybrid_llm_validated'
                        })
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            
        return results

    def _fallback_validation(self, candidates: List[FormulaCandidate]) -> List[Dict[str, Any]]:
        """Fallback validation using enhanced regex rules"""
        results = []
        
        for candidate in candidates:
            # Enhanced validation rules
            text = candidate.text.lower()
            
            # Skip if contains document numbers or dates
            if re.search(r'\b\d{2,4}/\d{4}\b', candidate.text):
                continue
                
            # Skip if too short or too generic
            if len(candidate.text.strip()) < 20:
                continue
                
            # Must contain mathematical indicators
            math_indicators = ['=', '×', 'x', '*', '/', '+', '-', '(', ')']
            if not any(indicator in candidate.text for indicator in math_indicators):
                continue
                
            # Boost confidence for Vietnamese education terms
            confidence = candidate.confidence
            education_terms = ['tiết', 'lương', 'định mức', 'giáo viên', 'học']
            if any(term in text for term in education_terms):
                confidence = min(1.0, confidence + 0.1)
                
            results.append({
                'name': candidate.text[:50] + '...' if len(candidate.text) > 50 else candidate.text,
                'formula': candidate.text,
                'type': candidate.pattern_type,
                'confidence': confidence,
                'context': candidate.context[:200],
                'extraction_method': 'hybrid_regex_validated'
            })
            
        return results

    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """Extract formulas directly from URL using Crawl4AI + hybrid approach"""
        logger.info(f"Starting hybrid extraction from URL: {url}")
        
        # Step 1: Get content using Crawl4AI or fallback
        content = await self._get_content_from_url(url)
        
        # Step 2: Extract using hybrid approach
        result = self.extract_formulas(content)
        result['url'] = url
        result['content_length'] = len(content)
        
        return result
    
    async def _get_content_from_url(self, url: str) -> str:
        """Get content from URL using Crawl4AI with LLM extraction"""
        if not self.use_crawl4ai:
            logger.warning("Crawl4AI not available, using basic extraction")
            return ""  # Fallback to manual content input
            
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                # Use LLM extraction for formulas
                extraction_strategy = {
                    "type": "llm",
                    "llm_config": {
                        "provider": "openai",
                        "model": "gpt-3.5-turbo",
                        "api_key": self.openai_api_key
                    },
                    "instruction": """
                    Extract all mathematical formulas, calculations, and numerical parameters from this Vietnamese legal document.
                    Focus on:
                    1. Salary calculations (tiền lương)
                    2. Teaching hour formulas (số tiết dạy)
                    3. Quota calculations (định mức)
                    4. Mathematical equations with =, ×, /, +, -
                    5. Percentage calculations
                    6. Limits and thresholds (không quá, tối đa, tối thiểu)
                    
                    Return the full text content with formulas clearly marked.
                    """
                }
                
                result = await crawler.arun(
                    url=url,
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True
                )
                
                if result.success:
                    # Combine extracted content with full markdown
                    content = result.extracted_content or result.markdown
                    logger.info(f"Crawl4AI extracted {len(content)} characters")
                    return content
                else:
                    logger.error(f"Crawl4AI failed: {result.error_message}")
                    return result.markdown or ""
                    
        except Exception as e:
            logger.error(f"Crawl4AI extraction failed: {e}")
            return ""
    
    def extract_formulas(self, text: str) -> Dict[str, Any]:
        """Main extraction method combining regex + LLM"""
        logger.info("Starting hybrid formula extraction...")
        
        # Step 1: Extract candidates with regex
        candidates = self.extract_candidates(text)
        logger.info(f"Found {len(candidates)} formula candidates")
        
        # Step 2: Validate with LLM or fallback
        validated_formulas = self.validate_with_llm(candidates)
        
        # Step 3: Extract parameters separately
        parameters = self._extract_parameters(text)
        
        # Step 4: Remove duplicates and sort by confidence
        unique_formulas = self._deduplicate_formulas(validated_formulas)
        unique_formulas.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'formulas': unique_formulas,
            'parameters': parameters,
            'total_formulas': len(unique_formulas),
            'total_parameters': len(parameters),
            'extraction_method': 'hybrid_crawl4ai_regex_llm' if self.use_crawl4ai else 'hybrid_regex_llm'
        }

    def _extract_parameters(self, text: str) -> List[Dict[str, Any]]:
        """Extract parameters (non-formula values)"""
        parameters = []
        
        for pattern, param_type, confidence in self.parameter_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                full_match = match.group(0).strip()
                value = match.group(2) if match.lastindex >= 2 else ""
                
                parameters.append({
                    'name': match.group(1).strip(),
                    'value': value,
                    'full_text': full_match,
                    'type': param_type,
                    'confidence': confidence
                })
                
        return parameters

    def _deduplicate_formulas(self, formulas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate formulas based on similarity"""
        if not formulas:
            return []
            
        unique = []
        for formula in formulas:
            is_duplicate = False
            for existing in unique:
                # Check similarity (simple approach)
                if (self._similarity(formula['formula'], existing['formula']) > 0.8 or
                    abs(len(formula['formula']) - len(existing['formula'])) < 10):
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                unique.append(formula)
                
        return unique

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple approach)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


async def main():
    """Test the hybrid extractor with Crawl4AI"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize extractor
    openai_key = os.getenv('OPENAI_API_KEY')
    extractor = HybridFormulaExtractor(openai_api_key=openai_key, use_crawl4ai=True)
    
    # Test URL
    test_url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    try:
        # Extract directly from URL using Crawl4AI
        result = await extractor.extract_from_url(test_url)
        
        # Save results
        output_file = 'data/hybrid_crawl4ai_result.json'
        os.makedirs('data', exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Hybrid Crawl4AI extraction completed!")
        print(f"📊 Found {result['total_formulas']} formulas, {result['total_parameters']} parameters")
        print(f"💾 Results saved to: {output_file}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"📄 Content length: {result.get('content_length', 0)} characters")
        
        # Display top results
        for i, formula in enumerate(result['formulas'][:3], 1):
            print(f"\n{i}. {formula['name'][:60]}...")
            print(f"   Formula: {formula['formula'][:100]}...")
            print(f"   Type: {formula['type']}")
            print(f"   Confidence: {formula['confidence']:.2f}")
            
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        
        # Fallback to sample text
        print("\n⚠️  Falling back to sample text extraction...")
        sample_text = """
        Số tiết dạy thêm của nhà giáo/năm học = (Tổng số tiết dạy được tính thực tế/năm học) - (Định mức tiết dạy/năm học)
        
        Tiền lương dạy thêm giờ/năm học = Số tiết dạy thêm/năm học × Tiền lương 01 tiết dạy thêm
        
        Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
        
        Số tiết dạy thêm không quá 200 tiết/năm học.
        
        Mức lương cơ bản tối thiểu là 1.800.000 đồng/tháng.
        """
        
        result = extractor.extract_formulas(sample_text)
        result.update({
            'url': test_url,
            'content_length': len(sample_text)
        })
        
        output_file = 'data/hybrid_fallback_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Fallback extraction completed!")
        print(f"📊 Found {result['total_formulas']} formulas, {result['total_parameters']} parameters")
        print(f"💾 Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
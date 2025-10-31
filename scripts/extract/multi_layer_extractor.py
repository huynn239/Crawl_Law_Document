#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-layer Formula Extraction với thống kê chi tiết"""
import json
import sys
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from crawl4ai import AsyncWebCrawler, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

class ExtractionStats(BaseModel):
    """Thống kê extraction chi tiết"""
    total_documents: int = 0
    total_detected_formulas: int = 0
    regex_extracted: int = 0
    llm_extracted: int = 0
    manual_required: int = 0
    success_rate: float = 0.0
    cost_estimation: float = 0.0

class FormulaCandidate(BaseModel):
    """Ứng viên công thức được detect"""
    text: str
    confidence: float
    method: str  # "regex", "llm", "manual"
    context: str

class MultiLayerExtractor:
    def __init__(self):
        self.stats = ExtractionStats()
        self.manual_queue = []  # Queue cho manual processing
        
    def detect_formula_candidates(self, text: str) -> List[FormulaCandidate]:
        """Layer 1: Detect tất cả ứng viên công thức"""
        candidates = []
        
        # Pattern rộng để detect potential formulas
        broad_patterns = [
            r'[^.]*?(?:=|:)\s*[\d.,]+\s*(?:đồng|VNĐ|%)[^.]*',
            r'[^.]*?(?:lương|phụ cấp|thuế|phí|tiền)[^.]*?[\d.,]+[^.]*',
            r'[^.]*?[\d.,]+\s*%[^.]*?(?:×|\*|của)[^.]*',
            r'[^.]*?(?:mức|tỷ lệ)[^.]*?[\d.,]+[^.]*',
            r'[^.]*?(?:tính|bằng)[^.]*?[\d.,]+[^.]*',
        ]
        
        for pattern in broad_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                candidate_text = match.group(0).strip()
                if len(candidate_text) > 10 and len(candidate_text) < 500:
                    candidates.append(FormulaCandidate(
                        text=candidate_text,
                        confidence=0.5,  # Initial confidence
                        method="detected",
                        context=candidate_text[:100]
                    ))
        
        # Remove duplicates
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c.text not in seen:
                seen.add(c.text)
                unique_candidates.append(c)
        
        self.stats.total_detected_formulas += len(unique_candidates)
        return unique_candidates[:50]  # Limit candidates
    
    def extract_with_regex(self, candidates: List[FormulaCandidate]) -> List[FormulaCandidate]:
        """Layer 2: Extract bằng regex patterns chính xác"""
        extracted = []
        
        # Precise patterns for actual formulas
        precise_patterns = [
            (r'([A-Za-zÀ-ỹ\s]{5,50})\s*=\s*([\d.,]+(?:\s*(?:đồng|VNĐ|%))?)(?:\s*/\s*[A-Za-zÀ-ỹ]+)?', 0.9),
            (r'([\d.,]+)\s*%\s*(?:của|×|\*)\s*([\d.,]+(?:\s*(?:đồng|VNĐ))?)', 0.8),
            (r'([A-Za-zÀ-ỹ\s]{5,40})\s*=\s*([\d.,]+)\s*([+\-×*/])\s*([\d.,]+)(?:\s*(?:đồng|VNĐ|%))?', 0.9),
            (r'((?:mức|tỷ\s*lệ)\s*[^:]{5,40}):\s*([\d.,]+\s*(?:%|đồng|VNĐ))', 0.7),
        ]
        
        for candidate in candidates:
            for pattern, confidence in precise_patterns:
                if re.search(pattern, candidate.text, re.IGNORECASE):
                    # Validate formula quality
                    if self._is_valid_formula(candidate.text):
                        candidate.confidence = confidence
                        candidate.method = "regex"
                        extracted.append(candidate)
                        break
        
        self.stats.regex_extracted += len(extracted)
        return extracted
    
    def _is_valid_formula(self, text: str) -> bool:
        """Validate formula quality"""
        # Must contain numbers and calculation indicators
        has_numbers = bool(re.search(r'\d', text))
        has_calc = any(op in text for op in ['=', '%', '+', '-', '×', '*', '/'])
        has_keywords = any(word in text.lower() for word in 
                          ['lương', 'phụ cấp', 'thuế', 'phí', 'tiền', 'mức', 'tỷ lệ', 'đồng', 'vnd'])
        
        # Must not contain invalid elements
        no_artifacts = not any(x in text.lower() for x in 
                              ['<', '>', 'href', 'class', 'div', 'span', 'javascript'])
        
        return has_numbers and has_calc and has_keywords and no_artifacts
    
    async def extract_with_llm(self, candidates: List[FormulaCandidate], url: str) -> List[FormulaCandidate]:
        """Layer 3: Extract bằng LLM cho cases phức tạp"""
        if not candidates:
            return []
        
        # Prepare text for LLM
        candidate_texts = [c.text for c in candidates]
        combined_text = "\n---\n".join(candidate_texts)
        
        prompt = f"""
        Phân tích các đoạn văn bản sau và xác định đâu là công thức tính toán thực sự:

        {combined_text}

        Trả về JSON với format:
        {{
          "valid_formulas": [
            {{
              "original_text": "text gốc",
              "formula": "công thức chuẩn hóa",
              "confidence": 0.9,
              "reason": "lý do"
            }}
          ]
        }}
        """
        
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                # Use Qwen 7B
                llm_config = LLMConfig(
                    provider="ollama/qwen:7b",
                    api_token=None,
                    base_url="http://localhost:8080"
                )
                
                extraction_strategy = LLMExtractionStrategy(
                    llm_config=llm_config,
                    extraction_type="text",
                    instruction=prompt
                )
                
                result = await crawler.arun(
                    url="data:text/html,<html><body>" + combined_text + "</body></html>",
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True
                )
                
                if result.success and result.extracted_content:
                    try:
                        llm_result = json.loads(result.extracted_content)
                        valid_formulas = llm_result.get("valid_formulas", [])
                        
                        extracted = []
                        for formula_data in valid_formulas:
                            original_text = formula_data.get("original_text", "")
                            # Find matching candidate
                            for candidate in candidates:
                                if original_text in candidate.text or candidate.text in original_text:
                                    candidate.confidence = formula_data.get("confidence", 0.8)
                                    candidate.method = "llm"
                                    extracted.append(candidate)
                                    break
                        
                        self.stats.llm_extracted += len(extracted)
                        return extracted
                        
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"LLM extraction failed: {e}")
        
        return []
    
    def queue_for_manual(self, candidates: List[FormulaCandidate]) -> List[FormulaCandidate]:
        """Layer 4: Queue remaining candidates for manual processing"""
        manual_candidates = []
        
        for candidate in candidates:
            if candidate.method == "detected":  # Not processed by regex or LLM
                candidate.method = "manual_required"
                manual_candidates.append(candidate)
                self.manual_queue.append({
                    "text": candidate.text,
                    "context": candidate.context,
                    "timestamp": datetime.now().isoformat()
                })
        
        self.stats.manual_required += len(manual_candidates)
        return manual_candidates
    
    async def process_document(self, url: str, cookies_path: Optional[str] = None) -> Dict:
        """Process một document với multi-layer extraction"""
        print(f"Processing: {url}")
        
        # Get document content
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=url,
                bypass_cache=True,
                js_code="""
                const tab1 = document.querySelector('#aNoiDung') || document.querySelector('a[href="#tab1"]');
                if (tab1) {
                    tab1.click();
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
                """,
                wait_for="networkidle"
            )
            
            if not result.success:
                return {"url": url, "error": result.error_message, "formulas": []}
            
            # Clean content
            clean_text = re.sub(r'<[^>]+>', ' ', result.cleaned_html)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Layer 1: Detect candidates
        candidates = self.detect_formula_candidates(clean_text)
        print(f"  Detected {len(candidates)} formula candidates")
        
        # Layer 2: Extract with regex
        regex_extracted = self.extract_with_regex(candidates.copy())
        print(f"  Regex extracted: {len(regex_extracted)}")
        
        # Layer 3: Extract remaining with LLM
        remaining_candidates = [c for c in candidates if c.method == "detected"]
        llm_extracted = await self.extract_with_llm(remaining_candidates, url)
        print(f"  LLM extracted: {len(llm_extracted)}")
        
        # Layer 4: Queue for manual
        still_remaining = [c for c in candidates if c.method == "detected"]
        manual_queued = self.queue_for_manual(still_remaining)
        print(f"  Manual required: {len(manual_queued)}")
        
        # Combine results
        all_extracted = regex_extracted + llm_extracted
        
        return {
            "url": url,
            "total_candidates": len(candidates),
            "regex_extracted": len(regex_extracted),
            "llm_extracted": len(llm_extracted),
            "manual_required": len(manual_queued),
            "formulas": [
                {
                    "text": f.text,
                    "method": f.method,
                    "confidence": f.confidence,
                    "context": f.context
                } for f in all_extracted
            ],
            "extraction_stats": {
                "success_rate": len(all_extracted) / len(candidates) if candidates else 0,
                "automation_rate": len(all_extracted) / len(candidates) if candidates else 0
            }
        }
    
    def generate_report(self) -> Dict:
        """Generate comprehensive extraction report"""
        total_processed = self.stats.regex_extracted + self.stats.llm_extracted + self.stats.manual_required
        
        if total_processed > 0:
            self.stats.success_rate = (self.stats.regex_extracted + self.stats.llm_extracted) / total_processed
        
        # Cost estimation (assuming manual work costs)
        manual_cost_per_formula = 10000  # VND per formula
        automation_savings = self.stats.manual_required * manual_cost_per_formula
        
        return {
            "extraction_summary": {
                "total_documents": self.stats.total_documents,
                "total_detected_formulas": self.stats.total_detected_formulas,
                "regex_extracted": self.stats.regex_extracted,
                "llm_extracted": self.stats.llm_extracted,
                "manual_required": self.stats.manual_required,
                "automation_rate": f"{(1 - self.stats.manual_required/max(1, self.stats.total_detected_formulas))*100:.1f}%",
                "success_rate": f"{self.stats.success_rate*100:.1f}%"
            },
            "cost_analysis": {
                "manual_work_saved": f"{automation_savings:,} VND",
                "manual_queue_size": len(self.manual_queue),
                "estimated_manual_hours": len(self.manual_queue) * 0.1  # 6 minutes per formula
            },
            "manual_queue": self.manual_queue[:10]  # Show first 10 items
        }

async def main():
    if len(sys.argv) < 2:
        print("Usage: python multi_layer_extractor.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_multi_layer.json"
    
    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    
    extractor = MultiLayerExtractor()
    results = []
    
    print(f"Processing {len(links)} documents with multi-layer extraction...")
    
    for idx, item in enumerate(links, 1):
        url = item.get("Url") or item.get("url", "")
        title = item.get("Tên văn bản") or item.get("title", "")
        
        print(f"\n[{idx}/{len(links)}] {title[:50]}...")
        
        try:
            result = await extractor.process_document(url)
            result["stt"] = idx
            result["title"] = title
            results.append(result)
            extractor.stats.total_documents += 1
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "stt": idx,
                "url": url,
                "title": title,
                "error": str(e)
            })
    
    # Generate final report
    final_report = {
        "extraction_report": extractor.generate_report(),
        "documents": results
    }
    
    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    
    # Print summary
    report = extractor.generate_report()
    print(f"\n{'='*60}")
    print("MULTI-LAYER EXTRACTION REPORT")
    print(f"{'='*60}")
    print(f"Documents processed: {report['extraction_summary']['total_documents']}")
    print(f"Total formulas detected: {report['extraction_summary']['total_detected_formulas']}")
    print(f"Regex extracted: {report['extraction_summary']['regex_extracted']}")
    print(f"LLM extracted: {report['extraction_summary']['llm_extracted']}")
    print(f"Manual required: {report['extraction_summary']['manual_required']}")
    print(f"Automation rate: {report['extraction_summary']['automation_rate']}")
    print(f"Manual work saved: {report['cost_analysis']['manual_work_saved']}")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
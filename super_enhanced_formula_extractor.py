#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super Enhanced Formula Extractor - Sử dụng 25+ regex patterns nâng cao"""
import re
import json
import asyncio
import sys
import os
from typing import Dict, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright
from enhanced_regex_patterns import EnhancedRegexPatterns

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class SuperEnhancedFormulaExtractor:
    def __init__(self):
        self.patterns_engine = EnhancedRegexPatterns()
        self.patterns = self.patterns_engine.get_patterns()
        
        # Additional specialized patterns for Vietnamese legal documents
        self.specialized_patterns = [
            # Công thức lương giáo viên
            {
                'name': 'Công thức lương giáo viên',
                'pattern': r'(tiền\s*lương\s*(?:01|1)\s*tiết\s*dạy[^=]{0,50})\s*=\s*([^.]{20,200})',
                'confidence': 0.98,
                'type': 'teacher_salary_formula'
            },
            
            # Định mức giờ dạy
            {
                'name': 'Định mức giờ dạy',
                'pattern': r'(định\s*mức\s*(?:giờ|tiết)\s*dạy[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*(?:tiết|giờ))',
                'confidence': 0.95,
                'type': 'teaching_quota'
            },
            
            # Số tuần dạy
            {
                'name': 'Số tuần dạy',
                'pattern': r'(số\s*tuần\s*(?:dạy|giảng\s*dạy)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*tuần)',
                'confidence': 0.9,
                'type': 'teaching_weeks'
            },
            
            # Tổng tiền lương
            {
                'name': 'Tổng tiền lương',
                'pattern': r'(tổng\s*(?:tiền\s*)?lương[^=:]{0,50})\s*[=:]\s*([^.]{10,100})',
                'confidence': 0.85,
                'type': 'total_salary'
            },
            
            # Công thức có phân số
            {
                'name': 'Công thức phân số',
                'pattern': r'([A-Za-zÀ-ỹ\s]{10,60})\s*=\s*([^/]{10,80})\s*/\s*([^.]{5,80})',
                'confidence': 0.8,
                'type': 'fraction_formula'
            }
        ]
        
        # Combine all patterns
        self.all_patterns = self.patterns + self.specialized_patterns
    
    def clean_text(self, text: str) -> str:
        """Làm sạch text nâng cao"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize Vietnamese currency
        text = re.sub(r'(?:VND|vnđ|VNĐ)', 'đồng', text, flags=re.IGNORECASE)
        
        # Normalize multiplication symbols
        text = re.sub(r'[×*]', '×', text)
        
        return text.strip()
    
    def calculate_confidence_score(self, match_text: str, base_confidence: float, pattern_info: Dict) -> float:
        """Tính điểm confidence nâng cao"""
        score = base_confidence
        match_lower = match_text.lower()
        
        # Boost từ patterns engine
        boost = self.patterns_engine.calculate_confidence_boost(match_text)
        score += boost
        
        # Boost đặc biệt cho các loại công thức quan trọng
        if pattern_info['type'] in ['teacher_salary_formula', 'salary_calculation', 'amount_definition']:
            score += 0.05
        
        # Penalty nếu quá ngắn hoặc quá dài
        if len(match_text) < 15:
            score -= 0.1
        elif len(match_text) > 200:
            score -= 0.05
        
        # Boost nếu có nhiều số
        number_count = len(re.findall(r'[0-9.,]+', match_text))
        if number_count >= 2:
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def is_valid_formula(self, match_text: str, pattern_info: Dict) -> bool:
        """Kiểm tra tính hợp lệ của công thức"""
        if not match_text or len(match_text.strip()) < 10:
            return False
        
        # Sử dụng patterns engine để kiểm tra loại trừ
        if self.patterns_engine.is_excluded(match_text):
            return False
        
        # Phải có ít nhất một số
        if not re.search(r'[0-9]', match_text):
            return False
        
        # Loại bỏ các trường hợp đặc biệt
        match_lower = match_text.lower()
        
        # Không được chứa quá nhiều ký tự đặc biệt
        special_chars = len(re.findall(r'[^\w\s\d.,+\-×*/÷=%:()àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', match_text))
        if special_chars > len(match_text) * 0.3:
            return False
        
        return True
    
    def extract_formulas_from_text(self, text: str) -> List[Dict]:
        """Trích xuất công thức từ text với thuật toán nâng cao"""
        if not text:
            return []
        
        results = []
        clean_text = self.clean_text(text)
        
        # Chia text thành các đoạn để xử lý tốt hơn
        paragraphs = [p.strip() for p in clean_text.split('\n') if p.strip() and len(p.strip()) > 20]
        
        for paragraph in paragraphs:
            for pattern_info in self.all_patterns:
                pattern = pattern_info['pattern']
                
                try:
                    matches = re.finditer(pattern, paragraph, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        match_text = match.group(0).strip()
                        
                        if self.is_valid_formula(match_text, pattern_info):
                            # Tính confidence score
                            confidence = self.calculate_confidence_score(
                                match_text, pattern_info['confidence'], pattern_info
                            )
                            
                            # Tạo tên công thức
                            formula_name = self.generate_formula_name(match, pattern_info)
                            
                            # Lấy ngữ cảnh
                            context = self.get_context(paragraph, match.start(), match.end())
                            
                            results.append({
                                'name': formula_name,
                                'formula': match_text,
                                'description': f"{pattern_info['name']} - {pattern_info['type']}",
                                'context': context,
                                'confidence': confidence,
                                'type': pattern_info['type'],
                                'extraction_method': 'super_enhanced_regex',
                                'groups': match.groups(),
                                'paragraph_preview': paragraph[:150] + "..." if len(paragraph) > 150 else paragraph
                            })
                            
                except re.error as e:
                    print(f"Regex error in pattern {pattern_info['name']}: {e}")
                    continue
        
        # Loại bỏ trùng lặp và sắp xếp
        results = self.deduplicate_results(results)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:25]  # Top 25 results
    
    def generate_formula_name(self, match, pattern_info: Dict) -> str:
        """Tạo tên cho công thức"""
        groups = match.groups()
        
        if groups and len(groups) > 0:
            first_group = groups[0].strip()
            if first_group and len(first_group) > 3:
                # Clean up the name
                name = re.sub(r'\s+', ' ', first_group)
                name = re.sub(r'[^\w\s\dàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', '', name)
                return name[:80]
        
        return pattern_info['name']
    
    def get_context(self, text: str, start: int, end: int, length: int = 200) -> str:
        """Lấy ngữ cảnh xung quanh công thức"""
        context_start = max(0, start - length)
        context_end = min(len(text), end + length)
        context = text[context_start:context_end].strip()
        
        # Highlight formula in context
        formula = text[start:end]
        if formula in context:
            context = context.replace(formula, f"**{formula}**")
        
        return context
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Loại bỏ kết quả trùng lặp thông minh"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Tạo key dựa trên formula content (normalized)
            formula_key = re.sub(r'\s+', ' ', result['formula'].lower().strip())
            formula_key = re.sub(r'[^\w\d%.,+\-×*/÷=:]', '', formula_key)
            
            # Tạo key ngắn hơn để tránh trùng lặp gần giống
            short_key = formula_key[:50] if len(formula_key) > 50 else formula_key
            
            if short_key not in seen and len(short_key) > 8:
                seen.add(short_key)
                unique_results.append(result)
        
        return unique_results
    
    async def extract_from_page(self, page, url: str) -> Dict:
        """Trích xuất công thức từ trang web"""
        try:
            # Click tab nội dung
            tab_selectors = ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')"]
            for selector in tab_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy nội dung từ nhiều nguồn
            content_methods = [
                ("#tab1", "Tab1 content"),
                ("#aNoiDung", "NoiDung tab"),
                (".tab-content", "Tab content area"),
                (".content", "Content area"),
                ("body", "Full body content")
            ]
            
            all_content = ""
            content_sources = []
            
            for selector, description in content_methods:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if content and len(content) > 100:
                            all_content += f"\n\n--- {description} ---\n{content}"
                            content_sources.append(description)
                            break  # Use first successful content source
                except:
                    continue
            
            if not all_content:
                all_content = await page.inner_text("body")
                content_sources = ["Body fallback"]
            
            # Trích xuất công thức
            formulas = self.extract_formulas_from_text(all_content)
            
            return {
                'url': url,
                'content_length': len(all_content),
                'content_sources': content_sources,
                'formulas': formulas,
                'total_formulas': len(formulas),
                'extraction_method': 'super_enhanced_25_patterns'
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'formulas': [],
                'total_formulas': 0
            }

async def main():
    if len(sys.argv) < 2:
        print("Usage: python super_enhanced_formula_extractor.py <input_file> [output_file]")
        print("Example: python super_enhanced_formula_extractor.py data/real_formula_links.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_super_enhanced.json"
    
    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"🚀 Super Enhanced Formula Extraction - Processing {len(links)} documents")
    print(f"📊 Using 25+ specialized regex patterns")
    
    extractor = SuperEnhancedFormulaExtractor()
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Load cookies if available
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        
        for idx, item in enumerate(links, 1):
            url = item.get("Url") or item.get("url", "")
            title = item.get("Tên văn bản") or item.get("title", "")
            
            print(f"[{idx}/{len(links)}] {title[:60]}...")
            
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                
                result = await extractor.extract_from_page(page, url)
                result["stt"] = idx
                result["title"] = title
                results.append(result)
                
                formulas_count = result.get("total_formulas", 0)
                if formulas_count > 0:
                    print(f"  ✅ Found {formulas_count} formulas")
                    # Show top formulas
                    for i, formula in enumerate(result["formulas"][:3], 1):
                        print(f"    {i}. [{formula['confidence']:.2f}] {formula['name'][:50]}")
                        print(f"       {formula['formula'][:80]}...")
                else:
                    print(f"  ❌ No formulas found")
                    if result.get('error'):
                        print(f"      Error: {result['error']}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results.append({
                    "stt": idx,
                    "url": url,
                    "title": title,
                    "error": str(e),
                    "formulas": [],
                    "total_formulas": 0
                })
            finally:
                await page.close()
        
        await browser.close()
    
    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Generate comprehensive summary
    total_formulas = sum(r.get("total_formulas", 0) for r in results)
    successful = len([r for r in results if r.get("total_formulas", 0) > 0])
    failed = len(results) - successful
    
    print(f"\n{'='*80}")
    print(f"🎯 SUPER ENHANCED FORMULA EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"📊 Documents processed: {len(results)}")
    print(f"✅ Successful extractions: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"❌ Failed extractions: {failed}")
    print(f"🔢 Total formulas found: {total_formulas}")
    print(f"📈 Average formulas per document: {total_formulas/len(results):.1f}")
    print(f"💾 Output saved to: {output_file}")
    
    # Analyze by formula type
    type_counts = {}
    confidence_stats = []
    
    for result in results:
        for formula in result.get("formulas", []):
            formula_type = formula.get("type", "unknown")
            type_counts[formula_type] = type_counts.get(formula_type, 0) + 1
            confidence_stats.append(formula.get("confidence", 0))
    
    if type_counts:
        print(f"\n📋 FORMULA TYPES FOUND:")
        for formula_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {formula_type}: {count} formulas")
    
    if confidence_stats:
        avg_confidence = sum(confidence_stats) / len(confidence_stats)
        print(f"\n📊 CONFIDENCE STATISTICS:")
        print(f"   Average confidence: {avg_confidence:.3f}")
        print(f"   High confidence (>0.9): {len([c for c in confidence_stats if c > 0.9])}")
        print(f"   Medium confidence (0.7-0.9): {len([c for c in confidence_stats if 0.7 <= c <= 0.9])}")
        print(f"   Low confidence (<0.7): {len([c for c in confidence_stats if c < 0.7])}")

if __name__ == "__main__":
    asyncio.run(main())
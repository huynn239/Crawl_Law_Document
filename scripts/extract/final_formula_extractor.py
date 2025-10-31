#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final Formula Extractor - Hệ thống trích xuất công thức cuối cùng với khả năng xử lý đa dạng"""
import re
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class FinalFormulaExtractor:
    def __init__(self):
        # Patterns mở rộng cho nhiều loại công thức
        self.patterns = [
            # 1. Mức tiền cụ thể
            {
                'name': 'Mức tiền cụ thể',
                'pattern': r'(mức\s+[^=:]{5,60})\s*[=:]\s*([\d.,]+(?:\s*(?:đồng|vnd|triệu|tỷ))?(?:/(?:tháng|năm|ngày))?)',
                'confidence': 0.95,
                'type': 'amount_definition'
            },
            
            # 2. Tỷ lệ phần trăm
            {
                'name': 'Tỷ lệ phần trăm',
                'pattern': r'(tỷ\s*lệ\s+[^:=]{5,60})\s*[=:]\s*([\d.,]+\s*(?:%|phần\s*trăm))',
                'confidence': 0.9,
                'type': 'percentage_rate'
            },
            
            # 3. Thuế suất
            {
                'name': 'Thuế suất',
                'pattern': r'(thuế\s*suất[^:=]{0,40})\s*[=:]\s*([\d.,]+\s*%)',
                'confidence': 0.95,
                'type': 'tax_rate'
            },
            
            # 4. Công thức tính thuế
            {
                'name': 'Công thức tính thuế',
                'pattern': r'(thuế[^=]{5,50})\s*=\s*([^.]{10,100}(?:×|x|\*)[^.]{5,50})',
                'confidence': 0.9,
                'type': 'tax_calculation'
            },
            
            # 5. Lương cơ bản/tối thiểu
            {
                'name': 'Lương cơ bản',
                'pattern': r'(lương\s*(?:cơ\s*bản|tối\s*thiểu|cơ\s*sở)[^=:]{0,40})\s*[=:]\s*([\d.,]+\s*(?:đồng|vnd)(?:/(?:tháng|năm))?)',
                'confidence': 0.95,
                'type': 'salary_base'
            },
            
            # 6. Phụ cấp
            {
                'name': 'Phụ cấp',
                'pattern': r'(phụ\s*cấp[^=:]{5,50})\s*[=:]\s*([\d.,]+(?:\s*(?:%|đồng|vnd))?)',
                'confidence': 0.85,
                'type': 'allowance'
            },
            
            # 7. Bảo hiểm
            {
                'name': 'Bảo hiểm',
                'pattern': r'(bảo\s*hiểm[^=:]{5,50})\s*[=:]\s*([\d.,]+\s*%)',
                'confidence': 0.9,
                'type': 'insurance_rate'
            },
            
            # 8. Lệ phí
            {
                'name': 'Lệ phí',
                'pattern': r'(lệ\s*phí[^:=]{5,60})\s*[=:]\s*([\d.,]+\s*(?:đồng|vnd))',
                'confidence': 0.85,
                'type': 'fee'
            },
            
            # 9. Khoảng tiền
            {
                'name': 'Khoảng tiền',
                'pattern': r'từ\s*([\d.,]+)\s*(?:đến|tới)\s*([\d.,]+)\s*(đồng|vnd|triệu|tỷ)',
                'confidence': 0.8,
                'type': 'money_range'
            },
            
            # 10. Giới hạn tiền
            {
                'name': 'Giới hạn tiền',
                'pattern': r'(không\s*(?:quá|vượt\s*quá|lớn\s*hơn|nhỏ\s*hơn))\s*([\d.,]+)\s*(đồng|vnd|triệu|tỷ)',
                'confidence': 0.75,
                'type': 'money_limit'
            },
            
            # 11. Phép tính đơn giản
            {
                'name': 'Phép tính',
                'pattern': r'([\d.,]+(?:\s*(?:đồng|%|triệu|tỷ))?)\s*([+\-×*/])\s*([\d.,]+(?:\s*(?:đồng|%|triệu|tỷ))?)',
                'confidence': 0.7,
                'type': 'calculation'
            },
            
            # 12. Công thức trong ngoặc
            {
                'name': 'Công thức trong ngoặc',
                'pattern': r'\(([^)]{15,100}(?:[\d.,]+(?:\s*(?:%|đồng|vnd))?[^)]*){1,})\)',
                'confidence': 0.6,
                'type': 'parenthetical'
            },
            
            # 13. Hệ số
            {
                'name': 'Hệ số',
                'pattern': r'(hệ\s*số[^=:]{5,50})\s*[=:]\s*([\d.,]+)',
                'confidence': 0.8,
                'type': 'coefficient'
            },
            
            # 14. Giảm trừ
            {
                'name': 'Giảm trừ',
                'pattern': r'(giảm\s*trừ[^=:]{5,50})\s*[=:]\s*([\d.,]+\s*(?:đồng|vnd)(?:/(?:tháng|năm))?)',
                'confidence': 0.9,
                'type': 'deduction'
            },
            
            # 15. Mức phạt
            {
                'name': 'Mức phạt',
                'pattern': r'((?:mức\s*)?phạt[^=:]{5,50})\s*[=:]\s*([\d.,]+(?:\s*(?:đồng|vnd|%|lần))?)',
                'confidence': 0.85,
                'type': 'penalty'
            }
        ]
        
        # Từ khóa loại trừ mạnh
        self.strong_exclude = [
            'điều', 'khoản', 'mục', 'chương', 'phụ lục', 'phần',
            'trang', 'tờ', 'số văn bản', 'quyết định số', 'thông tư số',
            'website', 'email', 'http', 'www', 'javascript', 'function',
            'ngày', 'tháng', 'năm', 'giờ', 'phút'
        ]
        
        # Từ khóa tích cực (tăng điểm)
        self.positive_keywords = [
            'tính', 'bằng', 'được xác định', 'theo công thức',
            'áp dụng', 'quy định', 'mức', 'tỷ lệ', 'thuế', 'phí',
            'lương', 'phụ cấp', 'bảo hiểm', 'giảm trừ'
        ]
    
    def clean_text(self, text: str) -> str:
        """Làm sạch text nâng cao"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Vietnamese and math symbols
        text = re.sub(r'[^\w\s\d.,+\-×*/÷=%:()àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', ' ', text)
        
        # Normalize Vietnamese currency
        text = re.sub(r'(?:VND|vnđ|VNĐ)', 'đồng', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def calculate_confidence_score(self, match_text: str, base_confidence: float) -> float:
        """Tính điểm confidence dựa trên nội dung"""
        score = base_confidence
        match_lower = match_text.lower()
        
        # Tăng điểm nếu có từ khóa tích cực
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in match_lower)
        score += positive_count * 0.05
        
        # Giảm điểm nếu có từ khóa loại trừ
        negative_count = sum(1 for keyword in self.strong_exclude if keyword in match_lower)
        score -= negative_count * 0.1
        
        # Tăng điểm nếu có số và đơn vị
        if re.search(r'[\d.,]+\s*(?:đồng|%|triệu|tỷ)', match_text):
            score += 0.1
        
        # Tăng điểm nếu có toán tử
        if any(op in match_text for op in ['=', '×', '*', '+', '-', '/']):
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def is_valid_match(self, match_text: str, pattern_info: Dict) -> bool:
        """Kiểm tra tính hợp lệ nâng cao"""
        if not match_text or len(match_text.strip()) < 8:
            return False
        
        match_lower = match_text.lower()
        
        # Loại bỏ các trường hợp rõ ràng không phải công thức
        for exclude in self.strong_exclude:
            if exclude in match_lower:
                return False
        
        # Loại bỏ ngày tháng
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', match_text):
            return False
        
        # Loại bỏ số văn bản
        if re.search(r'\d+/\d+/[A-Z-]+', match_text):
            return False
        
        # Phải có số
        if not re.search(r'\d', match_text):
            return False
        
        # Đối với một số pattern đặc biệt, kiểm tra thêm
        if pattern_info['type'] in ['tax_calculation', 'salary_base', 'insurance_rate']:
            # Phải có từ khóa mạnh
            required_keywords = {
                'tax_calculation': ['thuế'],
                'salary_base': ['lương'],
                'insurance_rate': ['bảo hiểm']
            }
            
            keywords = required_keywords.get(pattern_info['type'], [])
            if not any(keyword in match_lower for keyword in keywords):
                return False
        
        return True
    
    def extract_formulas_from_text(self, text: str) -> List[Dict]:
        """Trích xuất công thức từ text với thuật toán nâng cao"""
        if not text:
            return []
        
        results = []
        clean_text = self.clean_text(text)
        
        # Chia text thành các đoạn để xử lý
        paragraphs = [p.strip() for p in clean_text.split('\n') if p.strip()]
        
        for paragraph in paragraphs:
            if len(paragraph) < 20:  # Skip short paragraphs
                continue
            
            for pattern_info in self.patterns:
                pattern = pattern_info['pattern']
                matches = re.finditer(pattern, paragraph, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    match_text = match.group(0).strip()
                    
                    if self.is_valid_match(match_text, pattern_info):
                        # Tính confidence score
                        confidence = self.calculate_confidence_score(match_text, pattern_info['confidence'])
                        
                        # Tạo tên công thức
                        formula_name = self.generate_name(match, pattern_info)
                        
                        # Lấy ngữ cảnh
                        context = self.get_context(paragraph, match.start(), match.end())
                        
                        results.append({
                            'name': formula_name,
                            'formula': match_text,
                            'description': f"{pattern_info['name']} - {pattern_info['type']}",
                            'context': context,
                            'confidence': confidence,
                            'type': pattern_info['type'],
                            'groups': match.groups(),
                            'paragraph': paragraph[:200] + "..." if len(paragraph) > 200 else paragraph
                        })
        
        # Loại bỏ trùng lặp và sắp xếp
        results = self.deduplicate_results(results)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:20]  # Top 20 results
    
    def generate_name(self, match, pattern_info: Dict) -> str:
        """Tạo tên cho công thức"""
        groups = match.groups()
        
        if groups and len(groups) > 0:
            first_group = groups[0].strip()
            if first_group and len(first_group) > 3:
                return first_group[:60]
        
        return pattern_info['name']
    
    def get_context(self, text: str, start: int, end: int, length: int = 150) -> str:
        """Lấy ngữ cảnh xung quanh công thức"""
        context_start = max(0, start - length)
        context_end = min(len(text), end + length)
        context = text[context_start:context_end].strip()
        
        # Highlight formula in context
        formula = text[start:end]
        context = context.replace(formula, f"**{formula}**")
        
        return context
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Loại bỏ kết quả trùng lặp nâng cao"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Tạo key dựa trên formula content (normalized)
            formula_key = re.sub(r'\s+', ' ', result['formula'].lower().strip())
            formula_key = re.sub(r'[^\w\d%.,+\-×*/÷=:]', '', formula_key)
            
            if formula_key not in seen and len(formula_key) > 5:
                seen.add(formula_key)
                unique_results.append(result)
        
        return unique_results
    
    async def extract_from_page(self, page, url: str) -> Dict:
        """Trích xuất công thức từ trang web với nhiều phương pháp"""
        try:
            # Thử nhiều cách lấy nội dung
            content_methods = [
                ("#tab1", "Tab1 content"),
                ("#aNoiDung", "NoiDung tab"),
                (".tab-content", "Tab content area"),
                (".content", "Content area"),
                ("body", "Full body content")
            ]
            
            all_content = ""
            content_sources = []
            
            # Click tab nội dung nếu có
            tab_selectors = ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')"]
            for selector in tab_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy nội dung từ nhiều nguồn
            for selector, description in content_methods:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if content and len(content) > 100:
                            all_content += f"\\n\\n--- {description} ---\\n{content}"
                            content_sources.append(description)
                except:
                    continue
            
            if not all_content:
                # Fallback: lấy toàn bộ text
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
                'extraction_method': 'final_multi_source'
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
        print("Usage: python final_formula_extractor.py <input_file> [output_file]")
        print("Example: python final_formula_extractor.py data/real_formula_links.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_final.json"
    
    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"Final Formula Extraction - Processing {len(links)} documents")
    
    extractor = FinalFormulaExtractor()
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
    
    print(f"\\n{'='*80}")
    print(f"🎯 FINAL FORMULA EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"📊 Documents processed: {len(results)}")
    print(f"✅ Successful extractions: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"❌ Failed extractions: {failed}")
    print(f"🔢 Total formulas found: {total_formulas}")
    print(f"📈 Average formulas per document: {total_formulas/len(results):.1f}")
    print(f"💾 Output saved to: {output_file}")
    
    # Analyze by formula type
    type_counts = {}
    all_formulas = []
    
    for result in results:
        for formula in result.get("formulas", []):
            formula_type = formula.get("type", "unknown")
            type_counts[formula_type] = type_counts.get(formula_type, 0) + 1
            formula["source_title"] = result.get("title", "")
            all_formulas.append(formula)
    
    if type_counts:
        print(f"\\n📋 FORMULA TYPES FOUND:")
        for formula_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {formula_type}: {count} formulas")
    
    # Show top formulas by confidence
    if all_formulas:
        print(f"\\n🏆 TOP FORMULAS BY CONFIDENCE:")
        all_formulas.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        for i, formula in enumerate(all_formulas[:10], 1):
            print(f"{i:2d}. [{formula.get('confidence', 0):.2f}] {formula['name'][:50]}")
            print(f"     Formula: {formula['formula'][:100]}...")
            print(f"     Type: {formula.get('type', 'unknown')}")
            print(f"     Source: {formula['source_title'][:50]}...")
            print()

if __name__ == "__main__":
    asyncio.run(main())
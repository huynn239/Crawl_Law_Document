#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Improved Formula Extractor - Phiên bản cải tiến với patterns hoạt động tốt"""
import re
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class ImprovedFormulaExtractor:
    def __init__(self):
        # Patterns đã được test và hoạt động tốt
        self.patterns = [
            {
                'name': 'Mức tiền cụ thể',
                'pattern': r'(mức\s+[^=]{5,50})\s*=\s*([\d.,]+)\s*(đồng(?:/tháng|/năm|/ngày)?)',
                'confidence': 0.95,
                'type': 'amount_definition'
            },
            {
                'name': 'Tỷ lệ phần trăm',
                'pattern': r'(tỷ\s*lệ\s+[^:]{5,50}):\s*([\d.,]+\s*(?:%|phần\s*trăm))',
                'confidence': 0.9,
                'type': 'percentage_rate'
            },
            {
                'name': 'Công thức tính toán',
                'pattern': r'([^.]{10,60}(?:được\s*tính|tính\s*bằng|bằng))\s*=\s*([^.]{10,100})',
                'confidence': 0.85,
                'type': 'calculation_formula'
            },
            {
                'name': 'Phép nhân với tỷ lệ',
                'pattern': r'([^=×*]{10,50})\s*=\s*([\d.,]+\s*(?:%|phần\s*trăm))\s*[×*x]\s*([^.]{5,40})',
                'confidence': 0.8,
                'type': 'multiplication'
            },
            {
                'name': 'Lệ phí cụ thể',
                'pattern': r'(lệ\s*phí[^:]{5,50}):\s*([\d.,]+)\s*(đồng)',
                'confidence': 0.85,
                'type': 'fee_definition'
            },
            {
                'name': 'Khoảng tiền',
                'pattern': r'từ\s*([\d.,]+)\s*đến\s*([\d.,]+)\s*(đồng|triệu\s*đồng|tỷ\s*đồng)',
                'confidence': 0.8,
                'type': 'money_range'
            },
            {
                'name': 'Giới hạn tiền',
                'pattern': r'(không\s*(?:quá|vượt\s*quá|lớn\s*hơn))\s*([\d.,]+)\s*(đồng|triệu\s*đồng|tỷ\s*đồng)',
                'confidence': 0.75,
                'type': 'money_limit'
            },
            {
                'name': 'Phép cộng tiền',
                'pattern': r'([\d.,]+\s*(?:đồng|triệu|tỷ))\s*\+\s*([\d.,]+\s*(?:đồng|triệu|tỷ))',
                'confidence': 0.7,
                'type': 'addition'
            },
            {
                'name': 'Công thức thuế',
                'pattern': r'(thuế[^=]{5,40})\s*=\s*([^×*]{5,40})\s*[×*x]\s*([\d.,]+\s*(?:%|phần\s*trăm))',
                'confidence': 0.9,
                'type': 'tax_formula'
            },
            {
                'name': 'Công thức phụ cấp',
                'pattern': r'(phụ\s*cấp[^=]{0,40})\s*=\s*([\d.,]+\s*(?:%|phần\s*trăm))\s*[×*x]\s*([^.]{5,40})',
                'confidence': 0.85,
                'type': 'allowance_formula'
            }
        ]
        
        # Từ khóa loại trừ
        self.exclude_keywords = [
            'điều', 'khoản', 'mục', 'chương', 'phụ lục',
            'trang', 'tờ', 'số', 'quyết định', 'thông tư',
            'website', 'email', 'http', 'www', 'javascript'
        ]
    
    def clean_text(self, text: str) -> str:
        """Làm sạch text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep Vietnamese and math symbols
        text = re.sub(r'[^\w\s\d.,+\-×*/÷=%:()àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', ' ', text)
        return text.strip()
    
    def is_valid_match(self, match_text: str) -> bool:
        """Kiểm tra tính hợp lệ của match"""
        # Loại bỏ các trường hợp không hợp lệ
        match_lower = match_text.lower()
        
        # Kiểm tra từ khóa loại trừ
        for keyword in self.exclude_keywords:
            if keyword in match_lower:
                return False
        
        # Kiểm tra độ dài
        if len(match_text) < 10 or len(match_text) > 300:
            return False
        
        # Phải có số
        if not re.search(r'\d', match_text):
            return False
        
        # Loại bỏ ngày tháng
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', match_text):
            return False
        
        # Loại bỏ số văn bản
        if re.search(r'\d+/\d+/[A-Z-]+', match_text):
            return False
        
        return True
    
    def extract_formulas_from_text(self, text: str) -> List[Dict]:
        """Trích xuất công thức từ text"""
        results = []
        clean_text = self.clean_text(text)
        
        for pattern_info in self.patterns:
            pattern = pattern_info['pattern']
            matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                match_text = match.group(0).strip()
                
                if self.is_valid_match(match_text):
                    # Tạo tên công thức
                    formula_name = self.generate_name(match, pattern_info)
                    
                    # Lấy ngữ cảnh
                    context = self.get_context(clean_text, match.start(), match.end())
                    
                    results.append({
                        'name': formula_name,
                        'formula': match_text,
                        'description': f"{pattern_info['name']} - {pattern_info['type']}",
                        'context': context,
                        'confidence': pattern_info['confidence'],
                        'type': pattern_info['type'],
                        'groups': match.groups()
                    })
        
        # Loại bỏ trùng lặp và sắp xếp
        results = self.deduplicate_results(results)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:15]  # Top 15 results
    
    def generate_name(self, match, pattern_info: Dict) -> str:
        """Tạo tên cho công thức"""
        groups = match.groups()
        
        if pattern_info['type'] in ['amount_definition', 'fee_definition']:
            return groups[0].strip() if groups else pattern_info['name']
        elif pattern_info['type'] == 'percentage_rate':
            return groups[0].strip() if groups else 'Tỷ lệ'
        elif pattern_info['type'] in ['calculation_formula', 'tax_formula', 'allowance_formula']:
            left = groups[0].strip() if groups else ''
            return left[:50] if left else 'Công thức tính toán'
        elif pattern_info['type'] == 'multiplication':
            base = groups[0].strip() if groups else ''
            return f"Tính {base[:30]}" if base else 'Phép nhân'
        else:
            return pattern_info['name']
    
    def get_context(self, text: str, start: int, end: int, length: int = 100) -> str:
        """Lấy ngữ cảnh xung quanh công thức"""
        context_start = max(0, start - length)
        context_end = min(len(text), end + length)
        return text[context_start:context_end].strip()
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Loại bỏ kết quả trùng lặp"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Tạo key dựa trên formula content
            formula_key = re.sub(r'\s+', ' ', result['formula'].lower().strip())
            
            if formula_key not in seen and len(formula_key) > 10:
                seen.add(formula_key)
                unique_results.append(result)
        
        return unique_results
    
    async def extract_from_page(self, page, url: str) -> Dict:
        """Trích xuất công thức từ trang web"""
        try:
            # Click tab nội dung
            selectors = ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')", "#tab1"]
            clicked = False
            
            for selector in selectors:
                try:
                    await page.click(selector, timeout=2000)
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                await page.evaluate("() => { location.hash = '#tab1'; }")
            
            await page.wait_for_timeout(3000)
            
            # Lấy nội dung
            content = ""
            try:
                # Thử lấy tab1 trước
                tab1_element = await page.query_selector("#tab1")
                if tab1_element:
                    content = await tab1_element.inner_text()
                else:
                    # Fallback: lấy toàn bộ body
                    content = await page.inner_text("body")
            except:
                content = await page.inner_text("body")
            
            # Trích xuất công thức
            formulas = self.extract_formulas_from_text(content)
            
            return {
                'url': url,
                'content_length': len(content),
                'formulas': formulas,
                'total_formulas': len(formulas),
                'extraction_method': 'improved_patterns'
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
        print("Usage: python improved_formula_extractor.py <input_file> [output_file]")
        print("Example: python improved_formula_extractor.py data/real_formula_links.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_improved.json"
    
    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"Improved Formula Extraction - Processing {len(links)} documents")
    
    extractor = ImprovedFormulaExtractor()
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
                await page.wait_for_timeout(2000)
                
                result = await extractor.extract_from_page(page, url)
                result["stt"] = idx
                result["title"] = title
                results.append(result)
                
                formulas_count = result.get("total_formulas", 0)
                if formulas_count > 0:
                    print(f"  Found {formulas_count} formulas")
                    # Show top 2 formulas
                    for i, formula in enumerate(result["formulas"][:2], 1):
                        print(f"    {i}. [{formula['confidence']:.2f}] {formula['name']}")
                        print(f"       {formula['formula'][:80]}...")
                else:
                    print(f"  No formulas found")
                
            except Exception as e:
                print(f"  Error: {e}")
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
    
    # Generate summary
    total_formulas = sum(r.get("total_formulas", 0) for r in results)
    successful = len([r for r in results if r.get("total_formulas", 0) > 0])
    failed = len(results) - successful
    
    print(f"\n{'='*70}")
    print(f"IMPROVED FORMULA EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"Documents processed: {len(results)}")
    print(f"Successful extractions: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Failed extractions: {failed}")
    print(f"Total formulas found: {total_formulas}")
    print(f"Average formulas per document: {total_formulas/len(results):.1f}")
    print(f"Output saved to: {output_file}")
    
    # Show top formulas by confidence
    all_formulas = []
    for result in results:
        for formula in result.get("formulas", []):
            formula["source_title"] = result.get("title", "")
            all_formulas.append(formula)
    
    if all_formulas:
        print(f"\nTOP FORMULAS BY CONFIDENCE:")
        all_formulas.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        for i, formula in enumerate(all_formulas[:10], 1):
            print(f"{i:2d}. [{formula.get('confidence', 0):.2f}] {formula['name']}")
            print(f"     {formula['formula'][:100]}...")
            print(f"     Source: {formula['source_title'][:50]}...")
            print()

if __name__ == "__main__":
    asyncio.run(main())
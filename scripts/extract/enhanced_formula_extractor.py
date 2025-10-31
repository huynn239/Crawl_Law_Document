#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Formula Extractor - Trích xuất công thức tính toán từ văn bản pháp luật"""
import re
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from playwright.async_api import async_playwright
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class EnhancedFormulaExtractor:
    def __init__(self):
        # Từ khóa chỉ thị công thức
        self.formula_indicators = [
            'tính', 'bằng', 'được xác định', 'được tính', 'căn cứ', 'theo công thức',
            'mức', 'tỷ lệ', 'phần trăm', 'lương', 'phụ cấp', 'trợ cấp', 'thuế', 'phí',
            'tiền phạt', 'bồi thường', 'hỗ trợ', 'trích', 'nộp', 'đóng góp'
        ]
        
        # Đơn vị tiền tệ và tỷ lệ
        self.currency_units = ['đồng', 'vnd', 'vnđ', 'triệu', 'tỷ', 'nghìn']
        self.percentage_units = ['%', 'phần trăm', 'phần nghìn', '‰']
        
        # Toán tử
        self.operators = ['+', '-', '×', '*', '/', '÷', '=', ':', 'x']
        
        # Pattern cho số tiền Việt Nam
        self.money_pattern = r'[\d.,]+(?:\s*(?:đồng|vnd|vnđ|triệu|tỷ|nghìn))?'
        self.percentage_pattern = r'[\d.,]+\s*(?:%|phần\s*trăm|phần\s*nghìn|‰)'
        
    def clean_text(self, text: str) -> str:
        """Làm sạch text, loại bỏ HTML và ký tự không cần thiết"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep Vietnamese
        text = re.sub(r'[^\w\s\d.,+\-×*/÷=%:()àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', ' ', text)
        return text.strip()
    
    def extract_numerical_expressions(self, text: str) -> List[Dict]:
        """Trích xuất các biểu thức số học"""
        expressions = []
        
        # Pattern 1: Công thức có dấu = rõ ràng
        pattern1 = r'([^.]{10,100})\s*=\s*([^.]{5,80}(?:' + self.money_pattern + r'|' + self.percentage_pattern + r'))'
        matches = re.finditer(pattern1, text, re.IGNORECASE)
        for match in matches:
            left = self.clean_text(match.group(1))
            right = self.clean_text(match.group(2))
            if self.is_valid_formula(left, right):
                expressions.append({
                    'type': 'equation',
                    'left': left,
                    'right': right,
                    'full_text': match.group(0),
                    'confidence': 0.9
                })
        
        # Pattern 2: Mức/Tỷ lệ cụ thể
        pattern2 = r'((?:mức|tỷ\s*lệ|phần\s*trăm)\s*[^:]{5,50}):\s*(' + self.money_pattern + r'|' + self.percentage_pattern + r')'
        matches = re.finditer(pattern2, text, re.IGNORECASE)
        for match in matches:
            name = self.clean_text(match.group(1))
            value = self.clean_text(match.group(2))
            expressions.append({
                'type': 'rate_definition',
                'name': name,
                'value': value,
                'full_text': match.group(0),
                'confidence': 0.8
            })
        
        # Pattern 3: Phép tính có toán tử
        pattern3 = r'([^.]{10,80}(?:' + self.money_pattern + r'|' + self.percentage_pattern + r'))\s*([+\-×*/÷])\s*([^.]{5,80}(?:' + self.money_pattern + r'|' + self.percentage_pattern + r'))'
        matches = re.finditer(pattern3, text, re.IGNORECASE)
        for match in matches:
            operand1 = self.clean_text(match.group(1))
            operator = match.group(2)
            operand2 = self.clean_text(match.group(3))
            expressions.append({
                'type': 'calculation',
                'operand1': operand1,
                'operator': operator,
                'operand2': operand2,
                'full_text': match.group(0),
                'confidence': 0.7
            })
        
        # Pattern 4: Công thức trong ngoặc đơn
        pattern4 = r'\(([^)]{10,100}(?:' + self.money_pattern + r'|' + self.percentage_pattern + r')[^)]*)\)'
        matches = re.finditer(pattern4, text, re.IGNORECASE)
        for match in matches:
            formula = self.clean_text(match.group(1))
            if any(op in formula for op in self.operators):
                expressions.append({
                    'type': 'parenthetical',
                    'formula': formula,
                    'full_text': match.group(0),
                    'confidence': 0.6
                })
        
        return expressions
    
    def is_valid_formula(self, left: str, right: str) -> bool:
        """Kiểm tra xem có phải công thức hợp lệ không"""
        # Loại bỏ các trường hợp không phải công thức
        invalid_patterns = [
            r'điều\s*\d+', r'khoản\s*\d+', r'mục\s*\d+', r'chương\s*\d+',
            r'\d{1,2}/\d{1,2}/\d{4}', r'\d{4}-\d{4}',  # Ngày tháng
            r'số\s*\d+', r'quyết\s*định', r'thông\s*tư',  # Số văn bản
            r'trang\s*\d+', r'tờ\s*\d+',  # Số trang
        ]
        
        combined = left + ' ' + right
        for pattern in invalid_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return False
        
        # Phải có ít nhất một từ khóa chỉ thị công thức
        has_indicator = any(indicator in combined.lower() for indicator in self.formula_indicators)
        
        # Phải có số
        has_number = re.search(r'\d', combined)
        
        # Phải có đơn vị hoặc toán tử
        has_unit_or_operator = (
            any(unit in combined.lower() for unit in self.currency_units + self.percentage_units) or
            any(op in combined for op in self.operators)
        )
        
        return has_indicator and has_number and has_unit_or_operator
    
    def extract_contextual_formulas(self, text: str) -> List[Dict]:
        """Trích xuất công thức dựa trên ngữ cảnh"""
        formulas = []
        sentences = re.split(r'[.;!?]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            # Tìm câu có từ khóa công thức
            has_formula_keyword = any(keyword in sentence.lower() for keyword in self.formula_indicators)
            has_number = re.search(r'\d', sentence)
            has_operator = any(op in sentence for op in self.operators)
            
            if has_formula_keyword and has_number and (has_operator or 
                any(unit in sentence.lower() for unit in self.currency_units + self.percentage_units)):
                
                # Trích xuất các thành phần số học
                expressions = self.extract_numerical_expressions(sentence)
                
                if expressions:
                    formulas.append({
                        'sentence': sentence,
                        'expressions': expressions,
                        'context_score': len(expressions) * 0.3 + (1 if has_operator else 0) * 0.4
                    })
        
        return formulas
    
    def format_formula_result(self, expressions: List[Dict], contextual: List[Dict]) -> List[Dict]:
        """Định dạng kết quả cuối cùng"""
        results = []
        
        # Xử lý expressions trực tiếp
        for expr in expressions:
            if expr['confidence'] >= 0.7:
                if expr['type'] == 'equation':
                    results.append({
                        'name': expr['left'][:50],
                        'formula': f"{expr['left']} = {expr['right']}",
                        'description': f"Công thức tính {expr['left'].lower()}",
                        'context': expr['full_text'],
                        'confidence': expr['confidence'],
                        'type': 'direct_equation'
                    })
                elif expr['type'] == 'rate_definition':
                    results.append({
                        'name': expr['name'],
                        'formula': f"{expr['name']}: {expr['value']}",
                        'description': f"Định nghĩa {expr['name'].lower()}",
                        'context': expr['full_text'],
                        'confidence': expr['confidence'],
                        'type': 'rate_definition'
                    })
        
        # Xử lý contextual formulas
        for ctx in contextual:
            if ctx['context_score'] >= 0.5:
                for expr in ctx['expressions']:
                    if expr not in expressions:  # Tránh trùng lặp
                        results.append({
                            'name': f"Công thức từ ngữ cảnh",
                            'formula': expr.get('full_text', ''),
                            'description': "Công thức được trích xuất từ ngữ cảnh",
                            'context': ctx['sentence'][:200],
                            'confidence': ctx['context_score'],
                            'type': 'contextual'
                        })
        
        # Sắp xếp theo confidence và loại bỏ trùng lặp
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Remove duplicates based on formula content
        seen = set()
        unique_results = []
        for result in results:
            formula_key = result['formula'].lower().strip()
            if formula_key not in seen and len(formula_key) > 10:
                seen.add(formula_key)
                unique_results.append(result)
        
        return unique_results[:15]  # Top 15 formulas
    
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
            
            # Lấy nội dung tab1
            tab1_content = ""
            try:
                tab1_element = await page.query_selector("#tab1")
                if tab1_element:
                    tab1_content = await tab1_element.inner_text()
                else:
                    # Fallback: lấy toàn bộ nội dung trang
                    tab1_content = await page.inner_text("body")
            except:
                tab1_content = await page.inner_text("body")
            
            # Làm sạch text
            clean_content = self.clean_text(tab1_content)
            
            # Trích xuất công thức
            expressions = self.extract_numerical_expressions(clean_content)
            contextual = self.extract_contextual_formulas(clean_content)
            
            # Định dạng kết quả
            formulas = self.format_formula_result(expressions, contextual)
            
            return {
                'url': url,
                'content_length': len(clean_content),
                'raw_expressions': len(expressions),
                'contextual_matches': len(contextual),
                'formulas': formulas,
                'total_formulas': len(formulas),
                'extraction_method': 'enhanced_multi_layer'
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
        print("Usage: python enhanced_formula_extractor.py <input_file> [output_file]")
        print("Example: python enhanced_formula_extractor.py data/real_formula_links.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_file.parent / f"{input_file.stem}_enhanced.json"
    
    # Load links
    links = json.loads(input_file.read_text(encoding="utf-8"))
    print(f"🚀 Enhanced Formula Extraction - Processing {len(links)} documents")
    
    extractor = EnhancedFormulaExtractor()
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
                    print(f"  ✅ Found {formulas_count} formulas")
                    # Show sample
                    for i, formula in enumerate(result["formulas"][:2], 1):
                        print(f"    {i}. {formula['name']}: {formula['formula'][:80]}...")
                else:
                    print(f"  ❌ No formulas found")
                
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
    
    # Generate summary
    total_formulas = sum(r.get("total_formulas", 0) for r in results)
    successful = len([r for r in results if r.get("total_formulas", 0) > 0])
    failed = len(results) - successful
    
    print(f"\n{'='*70}")
    print(f"🎯 ENHANCED FORMULA EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"📊 Documents processed: {len(results)}")
    print(f"✅ Successful extractions: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"❌ Failed extractions: {failed}")
    print(f"🔢 Total formulas found: {total_formulas}")
    print(f"📈 Average formulas per document: {total_formulas/len(results):.1f}")
    print(f"💾 Output saved to: {output_file}")
    print(f"{'='*70}")
    
    # Show top formulas
    all_formulas = []
    for result in results:
        for formula in result.get("formulas", []):
            formula["source_title"] = result.get("title", "")
            all_formulas.append(formula)
    
    if all_formulas:
        print(f"\n🏆 TOP FORMULAS FOUND:")
        all_formulas.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        for i, formula in enumerate(all_formulas[:10], 1):
            print(f"{i:2d}. [{formula.get('confidence', 0):.2f}] {formula['name']}")
            print(f"     Formula: {formula['formula'][:100]}...")
            print(f"     Source: {formula['source_title'][:50]}...")
            print()

if __name__ == "__main__":
    asyncio.run(main())
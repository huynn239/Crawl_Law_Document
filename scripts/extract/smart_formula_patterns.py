#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smart Formula Patterns - Patterns thông minh cho trích xuất công thức pháp luật Việt Nam"""
import re
from typing import List, Dict, Tuple

class SmartFormulaPatterns:
    """Bộ patterns thông minh để nhận diện công thức trong văn bản pháp luật"""
    
    def __init__(self):
        # Từ khóa chỉ thị công thức mạnh
        self.strong_indicators = [
            'mức lương', 'mức phụ cấp', 'mức trợ cấp', 'mức thuế', 'mức phí',
            'tỷ lệ thuế', 'tỷ lệ phí', 'tỷ lệ đóng góp', 'tỷ lệ trích',
            'công thức tính', 'cách tính', 'được tính', 'được xác định',
            'tiền lương', 'tiền phạt', 'tiền bồi thường'
        ]
        
        # Từ khóa chỉ thị công thức yếu
        self.weak_indicators = [
            'bằng', 'tính', 'theo', 'căn cứ', 'dựa trên', 'quy định',
            'áp dụng', 'thực hiện', 'chi trả', 'nộp', 'đóng'
        ]
        
        # Đơn vị tiền tệ Việt Nam
        self.currency_patterns = [
            r'đồng(?:/tháng|/năm|/ngày)?',
            r'vn[dđ](?:/tháng|/năm|/ngày)?',
            r'triệu\s*đồng(?:/tháng|/năm|/ngày)?',
            r'tỷ\s*đồng(?:/tháng|/năm|/ngày)?',
            r'nghìn\s*đồng(?:/tháng|/năm|/ngày)?'
        ]
        
        # Pattern số tiền Việt Nam (có dấu phẩy, chấm)
        self.money_amount = r'[\d]{1,3}(?:[.,][\d]{3})*(?:[.,][\d]{1,2})?'
        
        # Tỷ lệ phần trăm
        self.percentage_patterns = [
            r'[\d.,]+\s*%',
            r'[\d.,]+\s*phần\s*trăm',
            r'[\d.,]+\s*phần\s*nghìn',
            r'[\d.,]+\s*‰'
        ]
        
        # Toán tử
        self.operators = ['+', '-', '×', '*', '/', '÷', '=', ':', 'x', 'X']
        
    def get_comprehensive_patterns(self) -> List[Dict]:
        """Trả về danh sách patterns toàn diện"""
        patterns = []
        
        # Pattern 1: Mức [tên] = [số tiền] đồng
        patterns.append({
            'name': 'Mức tiền cụ thể',
            'pattern': rf'(mức\s+[^=]{{5,40}})\s*=\s*({self.money_amount})\s*({"|".join(self.currency_patterns)})',
            'confidence': 0.95,
            'type': 'amount_definition'
        })
        
        # Pattern 2: Tỷ lệ [tên]: [số]%
        patterns.append({
            'name': 'Tỷ lệ phần trăm',
            'pattern': rf'(tỷ\s*lệ\s+[^:{{]{{5,40}}):\s*({"|".join(self.percentage_patterns)})',
            'confidence': 0.9,
            'type': 'percentage_rate'
        })
        
        # Pattern 3: [Tên] được tính = [công thức]
        patterns.append({
            'name': 'Công thức tính toán',
            'pattern': rf'([^.{{]{{10,50}}(?:được\s*tính|tính\s*bằng|bằng))\s*=\s*([^.{{]{{10,100}}(?:{self.money_amount}|{"|".join(self.percentage_patterns)}))',
            'confidence': 0.85,
            'type': 'calculation_formula'
        })
        
        # Pattern 4: Lương cơ bản × tỷ lệ
        patterns.append({
            'name': 'Phép nhân với tỷ lệ',
            'pattern': rf'([^×*]{{10,50}})\s*[×*]\s*({"|".join(self.percentage_patterns)}|{self.money_amount})',
            'confidence': 0.8,
            'type': 'multiplication'
        })
        
        # Pattern 5: [Số tiền] + [số tiền]
        patterns.append({
            'name': 'Phép cộng tiền',
            'pattern': rf'({self.money_amount}\s*(?:{"|".join(self.currency_patterns)}))\s*\+\s*({self.money_amount}\s*(?:{"|".join(self.currency_patterns)}))',
            'confidence': 0.75,
            'type': 'addition'
        })
        
        # Pattern 6: Thuế thu nhập = thu nhập × tỷ lệ
        patterns.append({
            'name': 'Công thức thuế',
            'pattern': rf'(thuế[^=]{{5,30}})\s*=\s*([^×*]{{5,30}})\s*[×*]\s*({"|".join(self.percentage_patterns)})',
            'confidence': 0.9,
            'type': 'tax_formula'
        })
        
        # Pattern 7: Phụ cấp = [tỷ lệ] × lương cơ bản
        patterns.append({
            'name': 'Công thức phụ cấp',
            'pattern': rf'(phụ\s*cấp[^=]{{0,30}})\s*=\s*({"|".join(self.percentage_patterns)})\s*[×*]\s*([^.{{]{{5,40}})',
            'confidence': 0.85,
            'type': 'allowance_formula'
        })
        
        # Pattern 8: Trong ngoặc đơn (công thức)
        patterns.append({
            'name': 'Công thức trong ngoặc',
            'pattern': rf'\(([^)]{{15,80}}(?:{self.money_amount}|{"|".join(self.percentage_patterns)})[^)]*)\)',
            'confidence': 0.7,
            'type': 'parenthetical'
        })
        
        # Pattern 9: Từ [số] đến [số] đồng
        patterns.append({
            'name': 'Khoảng tiền',
            'pattern': rf'từ\s*({self.money_amount})\s*đến\s*({self.money_amount})\s*({"|".join(self.currency_patterns)})',
            'confidence': 0.8,
            'type': 'money_range'
        })
        
        # Pattern 10: Không quá [số tiền]
        patterns.append({
            'name': 'Giới hạn tiền',
            'pattern': rf'(không\s*(?:quá|vượt\s*quá|lớn\s*hơn))\s*({self.money_amount})\s*({"|".join(self.currency_patterns)})',
            'confidence': 0.75,
            'type': 'money_limit'
        })
        
        return patterns
    
    def extract_with_patterns(self, text: str) -> List[Dict]:
        """Trích xuất công thức sử dụng patterns"""
        results = []
        patterns = self.get_comprehensive_patterns()
        
        # Làm sạch text
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                formula_text = match.group(0).strip()
                
                # Validate formula
                if self.is_valid_formula_match(formula_text, pattern_info):
                    # Extract components based on pattern type
                    components = self.extract_components(match, pattern_info)
                    
                    results.append({
                        'name': self.generate_formula_name(components, pattern_info),
                        'formula': formula_text,
                        'description': f"{pattern_info['name']} - {pattern_info['type']}",
                        'context': self.get_context(clean_text, match.start(), match.end()),
                        'confidence': pattern_info['confidence'],
                        'type': pattern_info['type'],
                        'components': components
                    })
        
        # Remove duplicates and sort by confidence
        results = self.deduplicate_results(results)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:20]  # Top 20 results
    
    def is_valid_formula_match(self, formula_text: str, pattern_info: Dict) -> bool:
        """Kiểm tra tính hợp lệ của match"""
        # Loại bỏ các trường hợp không phải công thức
        invalid_patterns = [
            r'điều\s*\d+', r'khoản\s*\d+', r'mục\s*\d+', r'chương\s*\d+',
            r'\d{1,2}/\d{1,2}/\d{4}', r'\d{4}-\d{4}',  # Ngày tháng
            r'số\s*\d+/\d+', r'quyết\s*định\s*số', r'thông\s*tư\s*số',  # Số văn bản
            r'trang\s*\d+', r'tờ\s*\d+', r'phụ\s*lục\s*\d+',  # Số trang
            r'website', r'email', r'http', r'www',  # Web content
            r'javascript', r'function', r'var\s+', r'document\.'  # Code
        ]
        
        for invalid_pattern in invalid_patterns:
            if re.search(invalid_pattern, formula_text, re.IGNORECASE):
                return False
        
        # Phải có độ dài hợp lý
        if len(formula_text) < 10 or len(formula_text) > 300:
            return False
        
        # Phải có số
        if not re.search(r'\d', formula_text):
            return False
        
        # Đối với một số loại pattern, cần kiểm tra thêm
        if pattern_info['type'] in ['calculation_formula', 'tax_formula', 'allowance_formula']:
            # Phải có từ khóa mạnh
            has_strong_indicator = any(indicator in formula_text.lower() 
                                     for indicator in self.strong_indicators)
            if not has_strong_indicator:
                return False
        
        return True
    
    def extract_components(self, match, pattern_info: Dict) -> Dict:
        """Trích xuất các thành phần của công thức"""
        components = {}
        groups = match.groups()
        
        if pattern_info['type'] == 'amount_definition':
            components = {
                'name': groups[0].strip() if len(groups) > 0 else '',
                'amount': groups[1].strip() if len(groups) > 1 else '',
                'currency': groups[2].strip() if len(groups) > 2 else ''
            }
        elif pattern_info['type'] == 'percentage_rate':
            components = {
                'name': groups[0].strip() if len(groups) > 0 else '',
                'rate': groups[1].strip() if len(groups) > 1 else ''
            }
        elif pattern_info['type'] in ['calculation_formula', 'tax_formula', 'allowance_formula']:
            components = {
                'left_side': groups[0].strip() if len(groups) > 0 else '',
                'right_side': groups[1].strip() if len(groups) > 1 else ''
            }
        elif pattern_info['type'] == 'multiplication':
            components = {
                'base': groups[0].strip() if len(groups) > 0 else '',
                'multiplier': groups[1].strip() if len(groups) > 1 else ''
            }
        elif pattern_info['type'] == 'money_range':
            components = {
                'min_amount': groups[0].strip() if len(groups) > 0 else '',
                'max_amount': groups[1].strip() if len(groups) > 1 else '',
                'currency': groups[2].strip() if len(groups) > 2 else ''
            }
        else:
            # Default: lưu tất cả groups
            for i, group in enumerate(groups):
                components[f'group_{i+1}'] = group.strip() if group else ''
        
        return components
    
    def generate_formula_name(self, components: Dict, pattern_info: Dict) -> str:
        """Tạo tên cho công thức"""
        if pattern_info['type'] == 'amount_definition':
            return components.get('name', 'Mức tiền')
        elif pattern_info['type'] == 'percentage_rate':
            return components.get('name', 'Tỷ lệ')
        elif pattern_info['type'] in ['calculation_formula', 'tax_formula', 'allowance_formula']:
            left = components.get('left_side', '')
            return left[:50] if left else 'Công thức tính toán'
        elif pattern_info['type'] == 'multiplication':
            base = components.get('base', '')
            return f"Tính toán {base[:30]}" if base else 'Phép nhân'
        elif pattern_info['type'] == 'money_range':
            return 'Khoảng tiền quy định'
        else:
            return pattern_info['name']
    
    def get_context(self, text: str, start: int, end: int, context_length: int = 100) -> str:
        """Lấy ngữ cảnh xung quanh công thức"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        context = text[context_start:context_end].strip()
        
        # Highlight the formula in context
        formula_in_context = text[start:end]
        context = context.replace(formula_in_context, f"**{formula_in_context}**")
        
        return context
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Loại bỏ kết quả trùng lặp"""
        seen_formulas = set()
        unique_results = []
        
        for result in results:
            # Tạo key dựa trên formula content (normalized)
            formula_key = re.sub(r'\s+', ' ', result['formula'].lower().strip())
            formula_key = re.sub(r'[^\w\d%.,+\-×*/÷=:]', '', formula_key)
            
            if formula_key not in seen_formulas and len(formula_key) > 5:
                seen_formulas.add(formula_key)
                unique_results.append(result)
        
        return unique_results

# Test function
def test_patterns():
    """Test patterns với một số ví dụ"""
    extractor = SmartFormulaPatterns()
    
    test_texts = [
        "Mức lương cơ bản = 1.800.000 đồng/tháng",
        "Tỷ lệ thuế thu nhập cá nhân: 10%",
        "Phụ cấp trách nhiệm được tính = 20% × lương cơ bản",
        "Thuế thu nhập = thu nhập chịu thuế × 15%",
        "Tiền phạt từ 500.000 đến 1.000.000 đồng",
        "Mức trợ cấp không quá 2.000.000 đồng/tháng",
        "Lương = lương cơ bản + phụ cấp + trợ cấp"
    ]
    
    print("🧪 Testing Smart Formula Patterns:")
    print("=" * 50)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. Input: {text}")
        results = extractor.extract_with_patterns(text)
        
        if results:
            for j, result in enumerate(results, 1):
                print(f"   Result {j}: {result['name']}")
                print(f"   Formula: {result['formula']}")
                print(f"   Confidence: {result['confidence']}")
                print(f"   Type: {result['type']}")
        else:
            print("   No formulas found")

if __name__ == "__main__":
    test_patterns()
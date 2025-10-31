#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Regex Patterns - Bộ regex mở rộng cho trích xuất công thức"""
import re
import sys
import os
from typing import List, Dict, Tuple

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class EnhancedRegexPatterns:
    def __init__(self):
        # Comprehensive regex patterns for Vietnamese legal documents (29 patterns)
        self.patterns = [
            # NEW: Multi-line và complex formula patterns (4 patterns mới)
            {
                'name': 'Multi-line Formula',
                'pattern': r'(?is)(tiền lương|số tiết|định mức)[^\n=]{0,100}\s*=\s*([\s\S]+?)(?=\n[A-ZÀ-Ỵ]|$)',
                'confidence': 0.92,
                'type': 'multi_line_formula'
            },
            {
                'name': 'Bracketed Formula',
                'pattern': r'(?i)([^\n]*\[.*?\]\s*[-–]\s*\(.*?\)[^\n]*)',
                'confidence': 0.88,
                'type': 'bracket_formula'
            },
            {
                'name': 'Compact Formula No Year',
                'pattern': r'(?i)(định mức tiết|thời gian công tác)[^=]{0,50}=\s*[^\n]+',
                'confidence': 0.85,
                'type': 'compact_formula'
            },
            {
                'name': 'Unicode Math Formula',
                'pattern': r'(?i)([^=\n]+=\s*[^=\n]*(×|÷|\*)[^=\n]+)',
                'confidence': 0.90,
                'type': 'unicode_math_formula'
            },
            
            # 1. Mức tiền cụ thể (Enhanced)
            {
                'name': 'Mức tiền cụ thể',
                'pattern': r'(mức\s+(?:lương|phí|thuế|phạt|trợ\s*cấp|phụ\s*cấp|bồi\s*thường)[^=:]{0,60})\s*[=:]\s*([0-9.,]+(?:\s*(?:đồng|vnd|triệu|tỷ|nghìn))?(?:/(?:tháng|năm|ngày|giờ|tiết))?)',
                'confidence': 0.95,
                'type': 'amount_definition'
            },
            
            # 2. Tỷ lệ phần trăm (Enhanced)
            {
                'name': 'Tỷ lệ phần trăm',
                'pattern': r'(tỷ\s*lệ\s+(?:thuế|phí|lãi\s*suất|chiết\s*khấu|giảm\s*giá|tăng\s*trưởng)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*(?:%|phần\s*trăm))',
                'confidence': 0.9,
                'type': 'percentage_rate'
            },
            
            # 3. Công thức tính lương (New)
            {
                'name': 'Công thức tính lương',
                'pattern': r'((?:tiền\s*)?lương[^=]{5,80})\s*=\s*([^.]{10,150}(?:×|x|\*|/)[^.]{5,100})',
                'confidence': 0.95,
                'type': 'salary_calculation'
            },
            
            # 4. Định mức/Định suất (New)
            {
                'name': 'Định mức',
                'pattern': r'(định\s*(?:mức|suất)\s+[^=:]{5,60})\s*[=:]\s*([0-9.,]+(?:\s*(?:tiết|giờ|ngày|tháng|%|đồng))?)',
                'confidence': 0.9,
                'type': 'quota_rate'
            },
            
            # 5. Thuế suất chi tiết (Enhanced)
            {
                'name': 'Thuế suất',
                'pattern': r'(thuế\s*(?:suất|thu\s*nhập|giá\s*trị\s*gia\s*tăng|xuất\s*nhập\s*khẩu)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*%)',
                'confidence': 0.95,
                'type': 'tax_rate'
            },
            
            # 6. Phụ cấp chi tiết (Enhanced)
            {
                'name': 'Phụ cấp',
                'pattern': r'((?:phụ\s*cấp|trợ\s*cấp)\s*(?:trách\s*nhiệm|độc\s*hại|xa\s*xôi|thâm\s*niên|chức\s*vụ)[^=:]{0,50})\s*[=:]\s*([0-9.,]+(?:\s*(?:%|đồng|vnd))?)',
                'confidence': 0.9,
                'type': 'allowance'
            },
            
            # 7. Bảo hiểm chi tiết (Enhanced)
            {
                'name': 'Bảo hiểm',
                'pattern': r'(bảo\s*hiểm\s*(?:xã\s*hội|y\s*tế|thất\s*nghiệp|tai\s*nạn)[^=:]{0,50})\s*[=:]\s*([0-9.,]+\s*%)',
                'confidence': 0.9,
                'type': 'insurance_rate'
            },
            
            # 8. Lệ phí chi tiết (Enhanced)
            {
                'name': 'Lệ phí',
                'pattern': r'(lệ\s*phí\s*(?:đăng\s*ký|cấp\s*phép|thẩm\s*định|kiểm\s*tra)[^:=]{0,60})\s*[=:]\s*([0-9.,]+\s*(?:đồng|vnd))',
                'confidence': 0.85,
                'type': 'fee'
            },
            
            # 9. Mức phạt chi tiết (Enhanced)
            {
                'name': 'Mức phạt',
                'pattern': r'((?:mức\s*)?phạt\s*(?:tiền|hành\s*chính|vi\s*phạm)[^=:]{0,60})\s*[=:]\s*([0-9.,]+(?:\s*(?:đồng|vnd|%|lần))?)',
                'confidence': 0.85,
                'type': 'penalty'
            },
            
            # 10. Khoảng giá trị (Enhanced)
            {
                'name': 'Khoảng giá trị',
                'pattern': r'từ\s*([0-9.,]+)\s*(?:đến|tới|→)\s*([0-9.,]+)\s*(đồng|vnd|triệu|tỷ|%)',
                'confidence': 0.8,
                'type': 'value_range'
            },
            
            # 11. Giới hạn (Enhanced)
            {
                'name': 'Giới hạn',
                'pattern': r'(không\s*(?:quá|vượt\s*quá|lớn\s*hơn|nhỏ\s*hơn|thấp\s*hơn|cao\s*hơn))\s*([0-9.,]+)\s*(đồng|vnd|triệu|tỷ|%|lần)',
                'confidence': 0.8,
                'type': 'limit'
            },
            
            # 12. Hệ số (Enhanced)
            {
                'name': 'Hệ số',
                'pattern': r'(hệ\s*số\s*(?:lương|điều\s*chỉnh|k|tăng\s*trưởng)[^=:]{0,50})\s*[=:]\s*([0-9.,]+)',
                'confidence': 0.85,
                'type': 'coefficient'
            },
            
            # 13. Giảm trừ (Enhanced)
            {
                'name': 'Giảm trừ',
                'pattern': r'(giảm\s*trừ\s*(?:gia\s*cảnh|bản\s*thân|người\s*phụ\s*thuộc)[^=:]{0,50})\s*[=:]\s*([0-9.,]+\s*(?:đồng|vnd)(?:/(?:tháng|năm))?)',
                'confidence': 0.9,
                'type': 'deduction'
            },
            
            # 14. Công thức trong bảng (New)
            {
                'name': 'Công thức bảng',
                'pattern': r'([A-Za-zÀ-ỹ\s]{10,60})\s*\|\s*=\s*\|\s*([^|]{10,100})',
                'confidence': 0.85,
                'type': 'table_formula'
            },
            
            # 15. Phép tính phức tạp (New)
            {
                'name': 'Phép tính phức tạp',
                'pattern': r'([0-9.,]+(?:\s*(?:đồng|%|triệu|tỷ))?)\s*([+\-×*/÷])\s*([0-9.,]+(?:\s*(?:đồng|%|triệu|tỷ))?)\s*([+\-×*/÷])\s*([0-9.,]+(?:\s*(?:đồng|%|triệu|tỷ))?)',
                'confidence': 0.75,
                'type': 'complex_calculation'
            },
            
            # 16. Công thức có điều kiện (New)
            {
                'name': 'Công thức có điều kiện',
                'pattern': r'(nếu|khi|trường\s*hợp)\s*([^,]{10,80}),?\s*(?:thì\s*)?([^.]{10,100}(?:[0-9.,]+(?:\s*(?:đồng|%|triệu|tỷ))?[^.]*){1,})',
                'confidence': 0.7,
                'type': 'conditional_formula'
            },
            
            # 17. Tỷ lệ đóng góp (New)
            {
                'name': 'Tỷ lệ đóng góp',
                'pattern': r'((?:người\s*lao\s*động|doanh\s*nghiệp|đơn\s*vị)\s*đóng)\s*([0-9.,]+\s*%)',
                'confidence': 0.85,
                'type': 'contribution_rate'
            },
            
            # 18. Mức tối thiểu/tối đa (New)
            {
                'name': 'Mức tối thiểu/tối đa',
                'pattern': r'(mức\s*(?:tối\s*thiểu|tối\s*đa|thấp\s*nhất|cao\s*nhất)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*(?:đồng|vnd|%|lần))',
                'confidence': 0.9,
                'type': 'min_max_amount'
            },
            
            # 19. Công thức chia (New)
            {
                'name': 'Công thức chia',
                'pattern': r'([A-Za-zÀ-ỹ\s]{10,60})\s*=\s*([A-Za-zÀ-ỹ\s0-9.,]{10,60})\s*/\s*([A-Za-zÀ-ỹ\s0-9.,]{5,60})',
                'confidence': 0.8,
                'type': 'division_formula'
            },
            
            # 20. Công thức nhân (New)
            {
                'name': 'Công thức nhân',
                'pattern': r'([A-Za-zÀ-ỹ\s]{10,60})\s*=\s*([A-Za-zÀ-ỹ\s0-9.,]{10,60})\s*(?:×|x|\*)\s*([A-Za-zÀ-ỹ\s0-9.,]{5,60})',
                'confidence': 0.8,
                'type': 'multiplication_formula'
            },
            
            # 21. Lãi suất (New)
            {
                'name': 'Lãi suất',
                'pattern': r'(lãi\s*suất\s*(?:cơ\s*bản|cho\s*vay|tiết\s*kiệm|thả\s*nổi)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*%(?:/(?:năm|tháng|ngày))?)',
                'confidence': 0.9,
                'type': 'interest_rate'
            },
            
            # 22. Tỷ giá (New)
            {
                'name': 'Tỷ giá',
                'pattern': r'(tỷ\s*giá\s*(?:USD|EUR|JPY|CNY)[^:=]{0,30})\s*[=:]\s*([0-9.,]+\s*(?:đồng|vnd))',
                'confidence': 0.85,
                'type': 'exchange_rate'
            },
            
            # 23. Chỉ số (New)
            {
                'name': 'Chỉ số',
                'pattern': r'(chỉ\s*số\s*(?:giá|lạm\s*phát|tăng\s*trưởng|CPI)[^:=]{0,50})\s*[=:]\s*([0-9.,]+\s*%)',
                'confidence': 0.8,
                'type': 'index'
            },
            
            # 24. Công thức trong ngoặc đơn (Enhanced)
            {
                'name': 'Công thức trong ngoặc',
                'pattern': r'\(([^)]{20,150}[0-9.,]+(?:\s*(?:%|đồng|vnd|×|x|\*|/|\+|-)).*?)\)',
                'confidence': 0.65,
                'type': 'parenthetical_formula'
            },
            
            # 25. Công thức theo quy định (New)
            {
                'name': 'Công thức theo quy định',
                'pattern': r'(theo\s*quy\s*định[^,]{10,60}),?\s*([^.]{10,100}(?:[0-9.,]+(?:\s*(?:đồng|%|triệu|tỷ))?[^.]*){1,})',
                'confidence': 0.7,
                'type': 'regulation_based'
            }
        ]
        
        # Từ khóa loại trừ mạnh
        self.strong_exclude = [
            r'\b(?:điều|khoản|mục|chương|phụ\s*lục|phần)\s*\d+',
            r'\b(?:trang|tờ)\s*\d+',
            r'\d+/\d+/[A-Z-]+',  # Số văn bản
            r'\d{1,2}/\d{1,2}/\d{4}',  # Ngày tháng
            r'(?:website|email|http|www|javascript|function)',
            r'(?:class|style|div|span|href)',
            r'(?:aspx|html|php)',
            r'listidlaw\d+',
            r'document\.',
            r'var\s+\w+',
            r'function\s*\(',
            r'return\s+',
            r'if\s*\(',
            r'for\s*\(',
            r'while\s*\('
        ]
        
        # Từ khóa tích cực (tăng confidence)
        self.positive_keywords = [
            'tính', 'bằng', 'được xác định', 'theo công thức', 'căn cứ',
            'áp dụng', 'quy định', 'mức', 'tỷ lệ', 'thuế', 'phí',
            'lương', 'phụ cấp', 'bảo hiểm', 'giảm trừ', 'hệ số',
            'định mức', 'định suất', 'lãi suất', 'tỷ giá', 'chỉ số'
        ]
    
    def get_patterns(self) -> List[Dict]:
        """Trả về danh sách 29 patterns (thêm 4 patterns mới cho multi-line formulas)"""
        return self.patterns
    
    def get_exclude_patterns(self) -> List[str]:
        """Trả về patterns loại trừ"""
        return self.strong_exclude
    
    def get_positive_keywords(self) -> List[str]:
        """Trả về từ khóa tích cực"""
        return self.positive_keywords
    
    def is_excluded(self, text: str) -> bool:
        """Kiểm tra text có bị loại trừ không"""
        text_lower = text.lower()
        for pattern in self.strong_exclude:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def calculate_confidence_boost(self, text: str) -> float:
        """Tính điểm tăng confidence dựa trên từ khóa tích cực"""
        text_lower = text.lower()
        boost = 0.0
        
        for keyword in self.positive_keywords:
            if keyword in text_lower:
                boost += 0.05
        
        # Tăng thêm nếu có số và đơn vị
        if re.search(r'[0-9.,]+\s*(?:đồng|%|triệu|tỷ|vnd)', text):
            boost += 0.1
        
        # Tăng thêm nếu có toán tử
        if any(op in text for op in ['=', '×', '*', '+', '-', '/', '÷']):
            boost += 0.05
        
        return min(0.3, boost)  # Tối đa tăng 0.3 điểm

# Test function
def test_patterns():
    """Test các patterns với nội dung mẫu"""
    patterns = EnhancedRegexPatterns()
    
    test_content = """
    1. Mức lương cơ bản: 1.800.000 đồng/tháng
    2. Tỷ lệ thuế thu nhập cá nhân: 10%
    3. Tiền lương 01 tiết dạy = Tổng tiền lương của 12 tháng × Số tuần giảng dạy / Định mức tiết dạy
    4. Định mức tiết dạy/năm học: 200 tiết
    5. Phụ cấp trách nhiệm = 20% × lương cơ bản
    6. Bảo hiểm xã hội: 8%
    7. Lệ phí đăng ký: 500.000 đồng
    8. Mức phạt vi phạm: từ 1.000.000 đến 5.000.000 đồng
    9. Hệ số lương K = 2.34
    10. Giảm trừ gia cảnh: 11.000.000 đồng/tháng
    """
    
    print("Testing Enhanced Regex Patterns")
    print("=" * 50)
    
    found_patterns = []
    
    for pattern_info in patterns.get_patterns():
        pattern = pattern_info['pattern']
        matches = re.finditer(pattern, test_content, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            match_text = match.group(0).strip()
            
            if not patterns.is_excluded(match_text) and len(match_text) > 10:
                confidence = pattern_info['confidence'] + patterns.calculate_confidence_boost(match_text)
                
                found_patterns.append({
                    'name': pattern_info['name'],
                    'formula': match_text,
                    'type': pattern_info['type'],
                    'confidence': min(1.0, confidence),
                    'groups': match.groups()
                })
    
    # Sort by confidence
    found_patterns.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"Found {len(found_patterns)} formulas:")
    for i, formula in enumerate(found_patterns, 1):
        print(f"\n{i}. [{formula['confidence']:.2f}] {formula['name']}")
        print(f"   Formula: {formula['formula']}")
        print(f"   Type: {formula['type']}")
        if formula['groups']:
            print(f"   Groups: {formula['groups']}")
    
    return len(found_patterns)

if __name__ == "__main__":
    test_patterns()
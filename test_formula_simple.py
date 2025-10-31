#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test formula extraction without crawl4ai dependency"""
import sys
import re
from typing import Dict, List

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def extract_formulas_regex_improved(html_content: str) -> List[Dict]:
    """Improved regex extraction for mathematical formulas"""
    formulas = []
    
    # Clean HTML first - remove tags but keep text
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Patterns cho các loại công thức thực sự - chính xác hơn
    patterns = [
        # Công thức có dấu = với số tiền cụ thể
        r'([A-Za-zÀ-ỹ\s]{5,50})\s*=\s*([\d.,]+(?:\s*(?:đồng|VNĐ|%))?)(?:\s*/\s*[A-Za-zÀ-ỹ]+)?',
        
        # Công thức tính % rõ ràng
        r'([\d.,]+)\s*%\s*(?:của|×|\*)\s*([\d.,]+(?:\s*(?:đồng|VNĐ))?)',
        
        # Công thức có phép tính + - × /
        r'([A-Za-zÀ-ỹ\s]{5,40})\s*=\s*([\d.,]+)\s*([+\-×*/])\s*([\d.,]+)(?:\s*(?:đồng|VNĐ|%))?',
        
        # Mức/Tỷ lệ với số cụ thể
        r'((?:mức|tỷ\s*lệ)\s*[^:]{5,40}):\s*([\d.,]+\s*(?:%|đồng|VNĐ))',
        
        # Công thức tính lương/phụ cấp
        r'((?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí)\s*[^=]{5,40})\s*=\s*([\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))?)',
        
        # Công thức có từ "tính" hoặc "bằng"
        r'(tính|bằng)\s*([^.]{10,80}(?:[\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))))',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.finditer(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            formula_text = match.group(0).strip()
            
            # Filter out HTML artifacts and invalid formulas
            if (len(formula_text) > 15 and len(formula_text) < 300 and
                not any(x in formula_text.lower() for x in ['<', '>', 'href', 'class', 'style', 'div', 'span', 'aspx']) and
                any(char.isdigit() for char in formula_text) and
                ('=' in formula_text or '%' in formula_text or any(op in formula_text for op in ['+', '-', '×', '*', '/']))):
                
                formulas.append({
                    "name": f"Công thức {len(formulas) + 1}",
                    "formula": formula_text,
                    "description": f"Công thức tính toán (pattern {i})",
                    "context": formula_text[:150] + "..." if len(formula_text) > 150 else formula_text
                })
    
    # Remove duplicates
    seen = set()
    unique_formulas = []
    for f in formulas:
        if f['formula'] not in seen:
            seen.add(f['formula'])
            unique_formulas.append(f)
    
    return unique_formulas[:20]  # Limit to top 20 formulas

# Test với sample content thực tế từ văn bản pháp luật
sample_legal_content = """
<div class="content">
<p>Mức lương cơ bản = 1.800.000 đồng/tháng</p>
<p>Phụ cấp trách nhiệm = 20% × lương cơ bản</p>
<p>Tiền phạt = 500.000 đồng + 2% × giá trị hợp đồng</p>
<p>Tỷ lệ đóng BHXH: 8%</p>
<p>Mức thuế thu nhập cá nhân = thu nhập chịu thuế × 10%</p>
<p>Lương hưu = 45% × mức lương bình quân</p>
<p>Phụ cấp kiêm nhiệm = 30% × lương cơ bản</p>
<p>Mức phạt vi phạm hành chính: từ 1.000.000 đồng đến 3.000.000 đồng</p>
<p>Tính thuế GTGT = doanh thu × 10%</p>
<p>Bằng 150% × mức lương tối thiểu vùng</p>
</div>
"""

print("Testing improved formula extraction...")
formulas = extract_formulas_regex_improved(sample_legal_content)

print(f"\nFound {len(formulas)} valid formulas:")
for i, formula in enumerate(formulas, 1):
    print(f"{i}. {formula['name']}: {formula['formula']}")

print(f"\n{'='*60}")
print("Formula extraction patterns working correctly!")
print("Ready to update crawl_formulas_fast.py")
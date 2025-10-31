#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Improved LLM Extractor v2.1 — Hỗ trợ multi-line, ngoặc, confidence động"""

import json
import re
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class ImprovedLLMExtractorV21:
    def __init__(self):
        self.improved_prompt = """
Bạn là chuyên gia trích xuất công thức tính toán từ văn bản pháp luật Việt Nam.

NHIỆM VỤ:
Trích xuất chính xác các biểu thức có dấu "=" hoặc phép toán (×, /, +, -, %) thể hiện công thức tính toán.

QUY TẮC:
- CHỈ giữ lại công thức có 2 vế logic (trái, phải) và có phép toán thật.
- LOẠI các dòng định nghĩa, ngày tháng, văn bản, hoặc câu mô tả.
- HỢP NHẤT các dòng công thức bị xuống hàng.

ĐỊNH DẠNG OUTPUT JSON:
{
  "formulas": [
    {"name": "Tên công thức", "formula": "Công thức đầy đủ", "description": "Giải thích ngắn", "confidence": 0.95, "type": "salary_calculation"}
  ]
}
"""

    def extract_with_improved_prompt(self, content: str) -> dict:
        """Extract công thức từ văn bản (giả lập LLM có prompt cải thiện)"""

        # --- 1️⃣ Pre-processing: giữ dòng có dấu = hoặc phép toán ---
        lines_with_math = []
        for line in content.splitlines():
            line = line.strip()
            if re.search(r'[=×÷*/%+\-]', line) and len(line) > 10:
                lines_with_math.append(line)

        # --- 2️⃣ Hợp nhất dòng nhiều dòng cùng công thức ---
        joined_lines = []
        buffer = ""
        for line in lines_with_math:
            if "=" in line and buffer:
                joined_lines.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line
        if buffer:
            joined_lines.append(buffer.strip())

        filtered_content = "\n".join(joined_lines)
        print(f"🧮 Filtered content length: {len(filtered_content)} chars\n")

        # --- 3️⃣ Regex extraction (multi-line, ngoặc, unicode) ---
        formula_patterns = [
            r'([^\n=]{8,120})\s*=\s*([\s\S]{8,250}?)(?=\n[A-ZÀ-Ỵ]|$)',
            r'([^\n=]{5,80})\s*=\s*([^\n=]{5,200}[×*/%+\-][^\n=]{3,200})',
        ]

        formulas = []
        for pattern in formula_patterns:
            matches = re.finditer(pattern, filtered_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                left = match.group(1).strip()
                right = match.group(2).strip()
                formula = f"{left} = {right}"
                formula = formula.replace('*', '×').replace('/', '÷')

                if self._is_valid_formula(formula):
                    formula_type = self._classify_formula_type(formula)
                    confidence = self._calculate_llm_confidence(formula)
                    formulas.append({
                        'name': self._extract_formula_name(left),
                        'formula': formula,
                        'description': f"Công thức {formula_type}",
                        'confidence': confidence,
                        'type': formula_type
                    })

        unique_formulas = self._deduplicate_formulas(formulas)
        return {
            'formulas': unique_formulas,
            'total_formulas': len(unique_formulas),
            'extraction_method': 'improved_llm_v2.1_with_multiline',
            'filtered_content_length': len(filtered_content),
            'original_content_length': len(content)
        }

    # --- Hỗ trợ các hàm phụ ---
    def _is_valid_formula(self, formula: str) -> bool:
        formula_lower = formula.lower()

        exclude_patterns = [
            r'\bđiều\s+\d+',
            r'\bkhoản\s+\d+',
            r'\bmục\s+\d+',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d+/\d+/[A-Z-]+',
            r'trang\s+\d+',
            r'http|email|đồng/tháng|mức lương cơ bản|tỷ lệ đóng'
        ]
        for pat in exclude_patterns:
            if re.search(pat, formula_lower):
                return False

        if not re.search(r'[×÷*/%+\-]|\d', formula):
            return False
        if len(formula) < 20 or len(formula) > 250:
            return False

        return True

    def _classify_formula_type(self, formula: str) -> str:
        f = formula.lower()
        if 'lương' in f or 'tiết dạy' in f:
            return 'salary_calculation'
        elif 'thuế' in f:
            return 'tax_calculation'
        elif '%' in f and ('×' in f or '÷' in f):
            return 'percentage_formula'
        elif '×' in f:
            return 'multiplication_formula'
        elif '÷' in f:
            return 'division_formula'
        else:
            return 'complex_formula'

    def _calculate_llm_confidence(self, formula: str) -> float:
        base = 0.75
        op_count = len(re.findall(r'[×÷*/%+\-]', formula))
        base += min(0.2, 0.03 * op_count)
        for kw in ['lương', 'thuế', 'phụ cấp', 'định mức', 'phí']:
            if kw in formula.lower():
                base += 0.03
        # Context awareness bonus
        if any(kw in formula.lower() for kw in ['tiết dạy', 'năm học']):
            base += 0.05
        return round(min(base, 0.98), 2)

    def _extract_formula_name(self, left_side: str) -> str:
        name = re.sub(r'^\d+\.\s*[a-z]\)\s*', '', left_side.strip())
        name = re.sub(r'^\d+[\.\)]\s*', '', name)
        name = re.sub(r'^[a-z]\)\s*', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name[:60]

    def _deduplicate_formulas(self, formulas: list) -> list:
        seen, unique = set(), []
        for f in formulas:
            key = re.sub(r'\s+', ' ', f['formula'].lower().strip())[:80]
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return sorted(unique, key=lambda x: x['confidence'], reverse=True)


# === 🧪 TEST ===
def test_improved_llm_v21():
    print("🤖 TESTING IMPROVED LLM EXTRACTOR v2.1")
    print("=" * 60)

    test_content = """
    Điều 5. Tiền lương dạy thêm giờ

    a) Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy) / (Định mức tiết dạy/năm học × 52 tuần)

    b) Tiền lương 01 tiết dạy = (Tổng tiền lương × Định mức tiết × 44 tuần) / (Định mức tiết × 1760 giờ × 52 tuần)

    c) Tiền lương 01 tiết dạy thêm = Tiền lương 01 tiết dạy × 150%

    d) Tiền lương dạy thêm giờ/năm = Số tiết × Tiền lương 01 tiết

    e) Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ/ngày) × (Số ngày/tuần) × (Số tuần/năm học)

    f) Tổng số tiết dạy thêm tối đa trong một năm học =
    [Tổng số tiết dạy các môn học/năm học + Tổng số tiết dạy khác] - (Tổng định mức tiết dạy/năm học)
    """

    extractor = ImprovedLLMExtractorV21()
    result = extractor.extract_with_improved_prompt(test_content)

    print(f"🧮 Found {result['total_formulas']} formulas")
    print("-" * 60)
    for i, f in enumerate(result['formulas'], 1):
        print(f"{i:2d}. [{f['confidence']:.2f}] {f['name']} → {f['type']}")
        print(f"    {f['formula']}\n")

    out_dir = "data/audit_results"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "improved_llm_v21_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"💾 Results saved to {out_file}\n✅ TEST COMPLETED\n")


if __name__ == "__main__":
    test_improved_llm_v21()

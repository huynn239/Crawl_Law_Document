#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production Ready Formula & Parameter Extractor - Hệ thống trích xuất sẵn sàng vận hành"""
import re
import json
import sys
import os
from typing import Dict, List
from core.patterns.regex_patterns import EnhancedRegexPatterns
from core.extractors.formula_separator import SmartFormulaSeparator

# Document Filter cho pre-filtering
class DocumentFilter:
    def __init__(self):
        self.formula_indicators = [r'=', r'×|÷|\*|/|%', r'[0-9.,]+\s*%', r'[0-9.,]+\s*đồng', r'công thức|cách tính']
        self.exclude_patterns = [r'^\s*điều\s+\d+', r'liên hệ|email|website']
    
    def has_formulas(self, content: str) -> bool:
        if not content or len(content) < 50:
            return False
        indicator_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in self.formula_indicators)
        exclusion_count = sum(1 for p in self.exclude_patterns if re.search(p, content, re.IGNORECASE))
        return (indicator_count - exclusion_count * 2) >= 1

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class ProductionReadyExtractor:
    def __init__(self):
        self.patterns_engine = EnhancedRegexPatterns()
        self.separator = SmartFormulaSeparator()
        self.document_filter = DocumentFilter()  # Thêm filter
        
    def extract_from_text(self, text: str) -> Dict:
        """Trích xuất và phân tách formulas + parameters từ text"""
        if not text:
            return self._empty_result()
        
        # Pre-filtering: Kiểm tra có công thức không
        if not self.document_filter.has_formulas(text):
            return {
                'formulas': [], 'parameters': [], 'total_formulas': 0, 'total_parameters': 0,
                'extraction_method': 'filtered_out_no_formulas', 'filter_applied': True
            }
        
        # Bước 1: Trích xuất tất cả bằng enhanced patterns
        raw_results = self._extract_raw_patterns(text)
        
        # Bước 2: Phân tách formulas vs parameters
        separated = self.separator.separate({
            'formulas': raw_results,
            'total_formulas': len(raw_results)
        })
        
        # Bước 3: Làm sạch và format kết quả
        return self._format_final_result(separated, text)
    
    def _extract_raw_patterns(self, text: str) -> List[Dict]:
        """Trích xuất patterns thô"""
        results = []
        clean_text = self._clean_text(text)
        
        # Chia text thành paragraphs
        paragraphs = [p.strip() for p in clean_text.split('\n') if p.strip() and len(p.strip()) > 20]
        
        for paragraph in paragraphs:
            for pattern_info in self.patterns_engine.get_patterns():
                try:
                    matches = re.finditer(pattern_info['pattern'], paragraph, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        match_text = match.group(0).strip()
                        
                        if self._is_valid_match(match_text, pattern_info):
                            confidence = self._calculate_confidence(match_text, pattern_info)
                            
                            results.append({
                                'name': self._generate_name(match, pattern_info),
                                'formula': match_text,
                                'description': f"{pattern_info['name']} - {pattern_info['type']}",
                                'context': self._get_context(paragraph, match.start(), match.end()),
                                'confidence': confidence,
                                'type': pattern_info['type'],
                                'extraction_method': 'production_enhanced_regex',
                                'groups': match.groups()
                            })
                            
                except re.error:
                    continue
        
        # Deduplicate và sort
        results = self._deduplicate(results)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results[:25]  # Top 25
    
    def _clean_text(self, text: str) -> str:
        """Làm sạch text"""
        if not text:
            return ""
        
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(?:VND|vnđ|VNĐ)', 'đồng', text, flags=re.IGNORECASE)
        text = re.sub(r'[×*]', '×', text)
        
        return text.strip()
    
    def _is_valid_match(self, match_text: str, pattern_info: Dict) -> bool:
        """Kiểm tra tính hợp lệ"""
        if not match_text or len(match_text.strip()) < 10:
            return False
        
        if self.patterns_engine.is_excluded(match_text):
            return False
        
        if not re.search(r'[0-9]', match_text):
            return False
        
        return True
    
    def _calculate_confidence(self, match_text: str, pattern_info: Dict) -> float:
        """Tính confidence score"""
        score = pattern_info['confidence']
        boost = self.patterns_engine.calculate_confidence_boost(match_text)
        score += boost
        
        # Penalty/bonus dựa trên độ dài
        if len(match_text) < 15:
            score -= 0.1
        elif len(match_text) > 200:
            score -= 0.05
        
        # Bonus cho công thức quan trọng
        if pattern_info['type'] in ['salary_calculation', 'fraction_formula']:
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _generate_name(self, match, pattern_info: Dict) -> str:
        """Tạo tên công thức"""
        groups = match.groups()
        
        if groups and len(groups) > 0:
            first_group = groups[0].strip()
            if first_group and len(first_group) > 3:
                name = re.sub(r'\s+', ' ', first_group)
                name = re.sub(r'[^\w\s\dàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', '', name)
                return name[:60]
        
        return pattern_info['name']
    
    def _get_context(self, text: str, start: int, end: int, length: int = 150) -> str:
        """Lấy context"""
        context_start = max(0, start - length)
        context_end = min(len(text), end + length)
        context = text[context_start:context_end].strip()
        
        formula = text[start:end]
        if formula in context:
            context = context.replace(formula, f"**{formula}**")
        
        return context
    
    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Loại bỏ trùng lặp"""
        seen = set()
        unique_results = []
        
        for result in results:
            formula_key = re.sub(r'\s+', ' ', result['formula'].lower().strip())
            formula_key = re.sub(r'[^\w\d%.,+\-×*/÷=:]', '', formula_key)
            short_key = formula_key[:50] if len(formula_key) > 50 else formula_key
            
            if short_key not in seen and len(short_key) > 8:
                seen.add(short_key)
                unique_results.append(result)
        
        return unique_results
    
    def _format_final_result(self, separated: Dict, original_text: str) -> Dict:
        """Format kết quả cuối cùng"""
        return {
            # Core results
            'formulas': separated['formulas'],
            'parameters': separated['parameters'],
            
            # Statistics
            'total_formulas': separated['total_formulas'],
            'total_parameters': separated['total_parameters'],
            'original_matches': separated['original_total'],
            
            # Metadata
            'content_length': len(original_text),
            'extraction_method': 'production_ready_25_patterns_with_separation',
            'separation_method': separated['separation_method'],
            
            # Quality metrics
            'formula_confidence_avg': self._calc_avg_confidence(separated['formulas']),
            'parameter_confidence_avg': self._calc_avg_confidence(separated['parameters']),
            
            # Summary by type
            'formula_types': self._count_types(separated['formulas']),
            'parameter_types': self._count_types(separated['parameters'])
        }
    
    def _calc_avg_confidence(self, items: List[Dict]) -> float:
        """Tính confidence trung bình"""
        if not items:
            return 0.0
        return sum(item.get('confidence', 0) for item in items) / len(items)
    
    def _count_types(self, items: List[Dict]) -> Dict[str, int]:
        """Đếm theo type"""
        counts = {}
        for item in items:
            t = item.get('type', 'unknown')
            counts[t] = counts.get(t, 0) + 1
        return counts
    
    def _empty_result(self) -> Dict:
        """Kết quả rỗng"""
        return {
            'formulas': [],
            'parameters': [],
            'total_formulas': 0,
            'total_parameters': 0,
            'original_matches': 0,
            'content_length': 0,
            'extraction_method': 'production_ready_empty',
            'formula_confidence_avg': 0.0,
            'parameter_confidence_avg': 0.0,
            'formula_types': {},
            'parameter_types': {}
        }

def demo_production_extractor():
    """Demo với nội dung thực tế"""
    
    # Nội dung mẫu từ văn bản pháp luật
    sample_content = """
    Điều 3. Cách tính tiền lương dạy thêm giờ
    
    1. Tiền lương của một tháng làm căn cứ tính trả tiền lương dạy thêm giờ của nhà giáo bao gồm: tiền lương tính theo hệ số lương (bao gồm phụ cấp thâm niên vượt khung nếu có) và các khoản phụ cấp chức vụ, phụ cấp trách nhiệm (nếu có).
    
    2. Tiền lương 01 tiết dạy thêm giờ được tính như sau:
    
    a) Đối với nhà giáo trong cơ sở giáo dục mầm non, phổ thông, thường xuyên, trung tâm giáo dục nghề nghiệp - giáo dục thường xuyên:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Số tuần giảng dạy hoặc dạy trẻ) / (Định mức tiết dạy/năm học × 52 tuần)
    
    b) Đối với nhà giáo trong cơ sở giáo dục đại học, cao đẳng sư phạm:
    
    Tiền lương 01 tiết dạy = (Tổng tiền lương của 12 tháng trong năm học × Định mức tiết dạy/năm học tính theo giờ hành chính × 44 tuần) / (Định mức tiết dạy/năm học × 1760 giờ × 52 tuần)
    
    3. Định mức tiết dạy/năm học:
    
    a) Định mức giờ dạy/năm học đối với giáo viên mầm non; định mức tiết dạy/năm học đối với giáo viên phổ thông: 200 tiết
    
    b) Định mức tiết dạy/năm học của giáo viên mầm non = (Số giờ dạy định mức/ngày) × (Số ngày làm việc/tuần) × (Số tuần dạy trẻ/năm học)
    
    4. Mức lương cơ bản hiện hành: 1.800.000 đồng/tháng
    
    5. Tỷ lệ đóng bảo hiểm xã hội: 8%
    
    6. Tỷ lệ đóng bảo hiểm y tế: 1.5%
    
    7. Phụ cấp trách nhiệm = 25% × mức lương cơ bản
    
    8. Giảm trừ gia cảnh: 11.000.000 đồng/tháng
    
    9. Thuế suất thuế thu nhập cá nhân: 10%
    
    10. Lệ phí đăng ký hồ sơ: 500.000 đồng
    
    11. Mức phạt vi phạm hành chính: từ 1.000.000 đến 5.000.000 đồng
    
    12. Hệ số lương K = 2.34
    
    13. Tổng số tiết dạy thêm trong một năm học không quá 200 tiết
    
    14. Lãi suất cho vay ưu đãi: 6.5%/năm
    
    15. Tỷ giá USD: 24.500 đồng
    
    16. Chỉ số giá tiêu dùng tăng: 3.2%
    """
    
    print("🚀 PRODUCTION READY EXTRACTOR DEMO")
    print("=" * 60)
    
    extractor = ProductionReadyExtractor()
    result = extractor.extract_from_text(sample_content)
    
    print(f"📊 EXTRACTION SUMMARY:")
    print(f"   Content length: {result['content_length']:,} chars")
    print(f"   Original matches: {result['original_matches']}")
    print(f"   🧮 True formulas: {result['total_formulas']}")
    print(f"   📋 Parameters: {result['total_parameters']}")
    print(f"   📈 Formula confidence: {result['formula_confidence_avg']:.3f}")
    print(f"   📊 Parameter confidence: {result['parameter_confidence_avg']:.3f}")
    
    print(f"\n🧮 TRUE FORMULAS (Có phép toán):")
    for i, formula in enumerate(result['formulas'], 1):
        print(f"{i:2d}. [{formula['confidence']:.2f}] {formula['name'][:50]}")
        print(f"    📝 {formula['formula'][:80]}...")
        print(f"    🏷️  {formula['type']}")
    
    print(f"\n📊 PARAMETERS (Tham số & Định nghĩa):")
    for i, param in enumerate(result['parameters'], 1):
        print(f"{i:2d}. [{param['confidence']:.2f}] {param['name'][:40]}")
        print(f"    💰 {param['value']}")
        print(f"    🏷️  {param['type']}")
    
    print(f"\n📈 FORMULA TYPES:")
    for t, count in sorted(result['formula_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {t}: {count}")
    
    print(f"\n📊 PARAMETER TYPES:")
    for t, count in sorted(result['parameter_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {t}: {count}")
    
    # Lưu kết quả
    with open('data/production_ready_demo_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Demo result saved to: data/production_ready_demo_result.json")
    print(f"\n✅ PRODUCTION READY EXTRACTOR: SUCCESS!")
    
    return result

if __name__ == "__main__":
    demo_production_extractor()
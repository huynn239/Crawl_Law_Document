#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gap Analyzer - BƯỚC 2: So sánh kết quả Regex vs LLM"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class GapAnalyzer:
    def __init__(self):
        pass

    def _load_json(self, file_path: Path) -> List[Dict]:
        """Tải dữ liệu từ tệp JSON"""
        if not file_path.exists():
            print(f"❌ Không tìm thấy tệp: {file_path}")
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Lỗi đọc tệp {file_path}: {e}")
            return []

    def _normalize_formula(self, formula_str: str) -> str:
        """Chuẩn hóa chuỗi công thức để so sánh"""
        import re
        cleaned = re.sub(r"\s+", " ", formula_str)
        cleaned = re.sub(r"[,;:]+", "", cleaned)
        cleaned = cleaned.replace("–", "-").replace("×", "*")
        return cleaned.strip().lower()

    def _compare_url_results(self, regex_result: Dict, llm_result: Dict) -> Dict:
        """So sánh kết quả của một URL"""
        
        url = regex_result.get('url') or llm_result.get('url')
        comparison = {
            'url': url,
            'regex_error': regex_result.get('error'),
            'llm_error': llm_result.get('error'),
            'regex_formulas_count': regex_result.get('total_formulas', 0),
            'llm_formulas_count': llm_result.get('total_formulas', 0),
            'regex_parameters_count': regex_result.get('total_parameters', 0),
            'llm_parameters_count': llm_result.get('total_parameters', 0),
            'missed_formulas_by_regex': [],  # LLM tìm thấy, Regex bỏ lỡ
            'missed_parameters_by_regex': [],
            'false_positive_formulas': [],  # Regex tìm thấy, LLM không thấy
            'false_positive_parameters': []
        }

        # Xử lý trường hợp lỗi
        if comparison['regex_error'] or comparison['llm_error']:
            return comparison

        # So sánh formulas
        regex_formulas = {
            self._normalize_formula(f.get('formula', '')): f 
            for f in regex_result.get('formulas', []) if f.get('formula')
        }
        llm_formulas = {
            self._normalize_formula(f.get('formula', '')): f 
            for f in llm_result.get('formulas', []) if f.get('formula')
        }

        regex_formula_keys = set(regex_formulas.keys())
        llm_formula_keys = set(llm_formulas.keys())

        # Formulas bị bỏ lỡ (MỤC TIÊU HỌC TẬP)
        missed_formula_keys = llm_formula_keys - regex_formula_keys
        comparison['missed_formulas_by_regex'] = [llm_formulas[key] for key in missed_formula_keys]
        
        # False positives (Cần xem xét)
        false_positive_formula_keys = regex_formula_keys - llm_formula_keys
        comparison['false_positive_formulas'] = [regex_formulas[key] for key in false_positive_formula_keys]

        # So sánh parameters
        regex_parameters = {
            self._normalize_formula(f"{p.get('name', '')}: {p.get('value', '')}"): p 
            for p in regex_result.get('parameters', []) if p.get('name')
        }
        llm_parameters = {
            self._normalize_formula(f"{p.get('name', '')}: {p.get('value', '')}"): p 
            for p in llm_result.get('parameters', []) if p.get('name')
        }

        regex_param_keys = set(regex_parameters.keys())
        llm_param_keys = set(llm_parameters.keys())

        # Parameters bị bỏ lỡ
        missed_param_keys = llm_param_keys - regex_param_keys
        comparison['missed_parameters_by_regex'] = [llm_parameters[key] for key in missed_param_keys]
        
        # False positive parameters
        false_positive_param_keys = regex_param_keys - llm_param_keys
        comparison['false_positive_parameters'] = [regex_parameters[key] for key in false_positive_param_keys]

        return comparison

    def analyze(self, regex_file: Path, llm_file: Path, output_dir: Path = None) -> Dict:
        """Chạy phân tích so sánh và lưu kết quả"""
        
        if output_dir is None:
            output_dir = Path("data/audit_results")
        
        print("🕵️ BƯỚC 2: Gap Analysis")
        print("=" * 50)
        print(f"📊 Hệ thống A (Regex): {regex_file.name}")
        print(f"🤖 Hệ thống B (LLM):   {llm_file.name}")
        
        regex_data = self._load_json(regex_file)
        llm_data = self._load_json(llm_file)

        if not regex_data or not llm_data:
            print("❌ Không thể tải dữ liệu. Dừng phân tích.")
            return {}

        # Map kết quả theo URL
        regex_map = {r['url']: r for r in regex_data}
        llm_map = {r['url']: r for r in llm_data}

        # Lấy tất cả URL
        all_urls = set(regex_map.keys()) | set(llm_map.keys())
        
        detailed_comparison = []
        total_missed_formulas = 0
        total_missed_parameters = 0
        total_false_positive_formulas = 0
        total_false_positive_parameters = 0

        print(f"\n🔍 Phân tích {len(all_urls)} URLs...")
        
        for i, url in enumerate(all_urls, 1):
            regex_result = regex_map.get(url, {'url': url, 'error': 'Missing result'})
            llm_result = llm_map.get(url, {'url': url, 'error': 'Missing result'})
            
            comp = self._compare_url_results(regex_result, llm_result)
            detailed_comparison.append(comp)
            
            missed_f = len(comp['missed_formulas_by_regex'])
            missed_p = len(comp['missed_parameters_by_regex'])
            false_f = len(comp['false_positive_formulas'])
            false_p = len(comp['false_positive_parameters'])
            
            total_missed_formulas += missed_f
            total_missed_parameters += missed_p
            total_false_positive_formulas += false_f
            total_false_positive_parameters += false_p
            
            if missed_f > 0 or missed_p > 0:
                print(f"  [{i:2d}] {url[:50]}... → Missed: {missed_f}F + {missed_p}P")

        # Tạo báo cáo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {
            'analysis_timestamp': timestamp,
            'regex_file': str(regex_file.name),
            'llm_file': str(llm_file.name),
            'total_urls_processed': len(all_urls),
            'summary': {
                'total_missed_formulas_by_regex': total_missed_formulas,
                'total_missed_parameters_by_regex': total_missed_parameters,
                'total_false_positive_formulas': total_false_positive_formulas,
                'total_false_positive_parameters': total_false_positive_parameters,
                'gap_score': total_missed_formulas + total_missed_parameters
            },
            'learning_targets': self._extract_learning_targets(detailed_comparison),
            'detailed_comparison': detailed_comparison
        }
        
        # Lưu báo cáo
        output_dir.mkdir(exist_ok=True)
        report_file = output_dir / f"gap_analysis_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # Export CSV for easy review
            self._export_csv_for_review(report, output_dir, timestamp)
            
            self._print_summary(report, report_file)
            
        except Exception as e:
            print(f"❌ Lỗi lưu báo cáo: {e}")

        return report

    def _extract_learning_targets(self, detailed_comparison: List[Dict]) -> Dict:
        """Trích xuất mục tiêu học tập từ phân tích chi tiết"""
        all_missed_formulas = []
        all_missed_parameters = []
        
        for comp in detailed_comparison:
            all_missed_formulas.extend(comp['missed_formulas_by_regex'])
            all_missed_parameters.extend(comp['missed_parameters_by_regex'])
        
        # Phân tích patterns bị lỡ
        formula_patterns = {}
        for formula in all_missed_formulas:
            formula_text = formula.get('formula', '')
            # Đơn giản hóa: tìm các từ khóa chính
            if '=' in formula_text and ('×' in formula_text or '*' in formula_text):
                formula_patterns['multiplication_with_equals'] = formula_patterns.get('multiplication_with_equals', 0) + 1
            elif '=' in formula_text and '/' in formula_text:
                formula_patterns['division_with_equals'] = formula_patterns.get('division_with_equals', 0) + 1
            elif 'nếu' in formula_text.lower():
                formula_patterns['conditional_formulas'] = formula_patterns.get('conditional_formulas', 0) + 1
        
        return {
            'missed_formulas_sample': all_missed_formulas[:5],  # Top 5 examples
            'missed_parameters_sample': all_missed_parameters[:5],
            'pattern_analysis': formula_patterns,
            'total_learning_opportunities': len(all_missed_formulas) + len(all_missed_parameters)
        }

    def _print_summary(self, report: Dict, report_file: Path):
        """In tóm tắt kết quả"""
        summary = report['summary']
        learning = report['learning_targets']
        
        print("\n" + "=" * 60)
        print("🎯 GAP ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"📊 URLs processed: {report['total_urls_processed']}")
        print(f"🎯 LEARNING TARGETS (Regex cần học):")
        print(f"   📝 Missed formulas: {summary['total_missed_formulas_by_regex']}")
        print(f"   📋 Missed parameters: {summary['total_missed_parameters_by_regex']}")
        print(f"   🔢 Total gap score: {summary['gap_score']}")
        print(f"\n⚠️  FALSE POSITIVES (Regex cần tinh chỉnh):")
        print(f"   📝 Extra formulas: {summary['total_false_positive_formulas']}")
        print(f"   📋 Extra parameters: {summary['total_false_positive_parameters']}")
        print(f"\n🎓 LEARNING OPPORTUNITIES: {learning['total_learning_opportunities']}")
        
        if learning['pattern_analysis']:
            print(f"\n🔍 PATTERN ANALYSIS:")
            for pattern, count in learning['pattern_analysis'].items():
                print(f"   {pattern}: {count} cases")
        
        print(f"\n💾 Detailed report: {report_file}")
        print("=" * 60)
        print("\n🚀 NEXT STEP: Review missed formulas and create new regex patterns!")

def main():
    if len(sys.argv) != 3:
        print("Usage: python gap_analyzer.py <regex_results.json> <llm_results.json>")
        print("Example: python gap_analyzer.py data/audit_results/regex_results_20250115_120000.json data/audit_results/llm_results_20250115_120000.json")
        sys.exit(1)
        
    regex_file = Path(sys.argv[1])
    llm_file = Path(sys.argv[2])
    
    if not regex_file.exists():
        print(f"❌ Regex file not found: {regex_file}")
        sys.exit(1)
    
    if not llm_file.exists():
        print(f"❌ LLM file not found: {llm_file}")
        sys.exit(1)

    analyzer = GapAnalyzer()
    analyzer.analyze(regex_file, llm_file)

if __name__ == "__main__":
    main()
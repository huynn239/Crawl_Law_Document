#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit Mode Runner - Chạy song song Regex vs LLM để so sánh"""
import asyncio
import json
import sys
import os
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from scripts.extract.regex_only_extractor import RegexOnlyExtractor
from scripts.extract.llm_only_extractor import LLMOnlyExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class AuditModeRunner:
    def __init__(self):
        self.regex_extractor = RegexOnlyExtractor()
        self.llm_extractor = LLMOnlyExtractor()
    
    async def run_batch(self, urls: List[str], output_dir: str = "data/audit_results") -> Dict:
        """Chạy audit mode trên batch URLs"""
        
        # Tạo thư mục output
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"🔄 AUDIT MODE - Processing {len(urls)} URLs")
        print(f"📊 System A: Regex Only")
        print(f"🤖 System B: LLM Only (Crawl4AI + Gemini)")
        print("=" * 60)
        
        results = {
            'timestamp': timestamp,
            'total_urls': len(urls),
            'regex_results': [],
            'llm_results': [],
            'summary': {}
        }
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Processing: {url[:60]}...")
            
            # Chạy song song cả hai hệ thống
            try:
                regex_task = self.regex_extractor.extract_from_url(url)
                llm_task = self.llm_extractor.extract_from_url(url)
                
                regex_result, llm_result = await asyncio.gather(regex_task, llm_task)
                
                # Lưu kết quả
                results['regex_results'].append(regex_result)
                results['llm_results'].append(llm_result)
                
                # In tóm tắt
                regex_formulas = regex_result.get('total_formulas', 0)
                regex_params = regex_result.get('total_parameters', 0)
                llm_formulas = llm_result.get('total_formulas', 0)
                llm_params = llm_result.get('total_parameters', 0)
                
                print(f"  📊 Regex: {regex_formulas} formulas, {regex_params} parameters")
                print(f"  🤖 LLM:   {llm_formulas} formulas, {llm_params} parameters")
                
                if regex_result.get('error'):
                    print(f"  ❌ Regex Error: {regex_result['error']}")
                if llm_result.get('error'):
                    print(f"  ❌ LLM Error: {llm_result['error']}")
                
                print()
                
            except Exception as e:
                print(f"  ❌ Error processing {url}: {e}")
                results['regex_results'].append({'url': url, 'error': str(e)})
                results['llm_results'].append({'url': url, 'error': str(e)})
        
        # Tính tóm tắt
        results['summary'] = self._calculate_summary(results)
        
        # Lưu kết quả
        regex_file = output_path / f"regex_results_{timestamp}.json"
        llm_file = output_path / f"llm_results_{timestamp}.json"
        summary_file = output_path / f"audit_summary_{timestamp}.json"
        
        with open(regex_file, 'w', encoding='utf-8') as f:
            json.dump(results['regex_results'], f, ensure_ascii=False, indent=2)
        
        with open(llm_file, 'w', encoding='utf-8') as f:
            json.dump(results['llm_results'], f, ensure_ascii=False, indent=2)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # In báo cáo cuối
        self._print_final_report(results, output_path)
        
        return results
    
    def _calculate_summary(self, results: Dict) -> Dict:
        """Tính tóm tắt kết quả"""
        regex_total_formulas = sum(r.get('total_formulas', 0) for r in results['regex_results'])
        regex_total_params = sum(r.get('total_parameters', 0) for r in results['regex_results'])
        
        llm_total_formulas = sum(r.get('total_formulas', 0) for r in results['llm_results'])
        llm_total_params = sum(r.get('total_parameters', 0) for r in results['llm_results'])
        
        regex_errors = len([r for r in results['regex_results'] if r.get('error')])
        llm_errors = len([r for r in results['llm_results'] if r.get('error')])
        
        return {
            'regex_stats': {
                'total_formulas': regex_total_formulas,
                'total_parameters': regex_total_params,
                'errors': regex_errors,
                'success_rate': (results['total_urls'] - regex_errors) / results['total_urls']
            },
            'llm_stats': {
                'total_formulas': llm_total_formulas,
                'total_parameters': llm_total_params,
                'errors': llm_errors,
                'success_rate': (results['total_urls'] - llm_errors) / results['total_urls']
            },
            'gap_analysis': {
                'formula_gap': llm_total_formulas - regex_total_formulas,
                'parameter_gap': llm_total_params - regex_total_params
            }
        }
    
    def _print_final_report(self, results: Dict, output_path: Path):
        """In báo cáo cuối cùng"""
        summary = results['summary']
        
        print("=" * 60)
        print("🎯 AUDIT MODE COMPLETE")
        print("=" * 60)
        print(f"📊 Total URLs processed: {results['total_urls']}")
        print()
        print("📈 SYSTEM A (Regex Only):")
        print(f"   Formulas: {summary['regex_stats']['total_formulas']}")
        print(f"   Parameters: {summary['regex_stats']['total_parameters']}")
        print(f"   Success rate: {summary['regex_stats']['success_rate']:.1%}")
        print(f"   Errors: {summary['regex_stats']['errors']}")
        print()
        print("🤖 SYSTEM B (LLM Only):")
        print(f"   Formulas: {summary['llm_stats']['total_formulas']}")
        print(f"   Parameters: {summary['llm_stats']['total_parameters']}")
        print(f"   Success rate: {summary['llm_stats']['success_rate']:.1%}")
        print(f"   Errors: {summary['llm_stats']['errors']}")
        print()
        print("🔍 GAP ANALYSIS:")
        print(f"   Formula gap: {summary['gap_analysis']['formula_gap']} (LLM - Regex)")
        print(f"   Parameter gap: {summary['gap_analysis']['parameter_gap']} (LLM - Regex)")
        print()
        print(f"💾 Results saved to: {output_path}")
        print("=" * 60)

async def main():
    """Test với URLs mẫu"""
    if len(sys.argv) < 2:
        print("Usage: python audit_mode_runner.py <input_file.json>")
        print("Example: python audit_mode_runner.py data/test_urls.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)
    
    # Load URLs
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract URLs
    if isinstance(data, list):
        if all('Url' in item for item in data):
            urls = [item['Url'] for item in data]
        elif all('url' in item for item in data):
            urls = [item['url'] for item in data]
        else:
            urls = data  # Assume it's a list of URLs
    else:
        print("Invalid input format. Expected list of URLs or objects with 'Url'/'url' field")
        sys.exit(1)
    
    # Run audit mode
    runner = AuditModeRunner()
    await runner.run_batch(urls[:10])  # Limit to 10 for testing

if __name__ == "__main__":
    asyncio.run(main())
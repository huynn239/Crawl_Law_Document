#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo Formula Extraction - Thử nghiệm với nội dung mẫu thực tế"""
import json
import sys
from pathlib import Path
from final_formula_extractor import FinalFormulaExtractor

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def demo_with_sample_content():
    """Demo với nội dung mẫu từ văn bản pháp luật thực tế"""
    
    # Nội dung mẫu từ các văn bản pháp luật Việt Nam
    sample_contents = [
        {
            "title": "Thông tư về thuế thu nhập cá nhân",
            "content": """
            Điều 5. Mức giảm trừ gia cảnh
            1. Mức giảm trừ gia cảnh cho người nộp thuế là 11.000.000 đồng/tháng.
            2. Mức giảm trừ gia cảnh cho mỗi người phụ thuộc là 4.400.000 đồng/tháng.
            
            Điều 6. Thuế suất thuế thu nhập cá nhân
            Thuế suất thuế thu nhập cá nhân được quy định như sau:
            - Đối với thu nhập từ 0 đến 5.000.000 đồng: 5%
            - Đối với thu nhập từ 5.000.001 đến 10.000.000 đồng: 10%
            - Đối với thu nhập từ 10.000.001 đến 18.000.000 đồng: 15%
            
            Điều 7. Cách tính thuế
            Thuế thu nhập cá nhân phải nộp = Thu nhập tính thuế × Thuế suất
            """
        },
        
        {
            "title": "Nghị định về bảo hiểm xã hội",
            "content": """
            Điều 10. Mức đóng bảo hiểm xã hội
            1. Mức đóng bảo hiểm xã hội bằng 8% mức lương đóng bảo hiểm xã hội.
            2. Mức đóng bảo hiểm y tế bằng 1,5% mức lương đóng bảo hiểm y tế.
            3. Mức đóng bảo hiểm thất nghiệp bằng 1% mức lương đóng bảo hiểm thất nghiệp.
            
            Điều 11. Lương tối thiểu vùng
            Mức lương tối thiểu vùng được quy định như sau:
            - Vùng I: 4.680.000 đồng/tháng
            - Vùng II: 4.160.000 đồng/tháng
            - Vùng III: 3.640.000 đồng/tháng
            - Vùng IV: 3.250.000 đồng/tháng
            """
        },
        
        {
            "title": "Nghị định về lương cán bộ công chức",
            "content": """
            Điều 3. Lương cơ sở
            Lương cơ sở áp dụng chung đối với cán bộ, công chức, viên chức và lực lượng vũ trang là 1.800.000 đồng/tháng.
            
            Điều 4. Phụ cấp trách nhiệm
            1. Phụ cấp trách nhiệm = Hệ số phụ cấp × Lương cơ sở
            2. Hệ số phụ cấp trách nhiệm được quy định từ 0,1 đến 2,0
            
            Điều 5. Phụ cấp thâm niên nghề
            Phụ cấp thâm niên nghề = Tỷ lệ phụ cấp × Lương cơ sở × Số năm công tác
            Tỷ lệ phụ cấp thâm niên: 5% cho mỗi 5 năm công tác
            """
        },
        
        {
            "title": "Thông tư về phí lệ phí",
            "content": """
            Điều 2. Lệ phí cấp giấy phép lái xe
            1. Lệ phí cấp giấy phép lái xe hạng A1: 135.000 đồng
            2. Lệ phí cấp giấy phép lái xe hạng A2: 135.000 đồng
            3. Lệ phí cấp giấy phép lái xe hạng B1: 270.000 đồng
            4. Lệ phí cấp giấy phép lái xe hạng B2: 270.000 đồng
            
            Điều 3. Phí sát hạch lái xe
            Phí sát hạch lái xe = Phí lý thuyết + Phí thực hành
            - Phí sát hạch lý thuyết: 70.000 đồng
            - Phí sát hạch thực hành: 120.000 đồng
            """
        },
        
        {
            "title": "Nghị định về xử phạt vi phạm hành chính",
            "content": """
            Điều 15. Mức phạt tiền
            1. Mức phạt tiền đối với cá nhân từ 50.000 đồng đến 75.000.000 đồng
            2. Mức phạt tiền đối với tổ chức từ 100.000 đồng đến 150.000.000 đồng
            
            Điều 16. Tính mức phạt
            Tiền phạt không quá 3 lần mức lương cơ sở tại thời điểm xử phạt
            
            Điều 17. Phạt bổ sung
            Phạt bổ sung = 10% × Giá trị hàng hóa vi phạm
            """
        }
    ]
    
    print("🎯 DEMO FORMULA EXTRACTION WITH SAMPLE CONTENT")
    print("=" * 70)
    
    extractor = FinalFormulaExtractor()
    all_results = []
    total_formulas = 0
    
    for i, sample in enumerate(sample_contents, 1):
        print(f"\\n📄 [{i}/{len(sample_contents)}] {sample['title']}")
        print("-" * 60)
        
        # Extract formulas
        formulas = extractor.extract_formulas_from_text(sample['content'])
        
        if formulas:
            print(f"✅ Found {len(formulas)} formulas:")
            total_formulas += len(formulas)
            
            for j, formula in enumerate(formulas, 1):
                print(f"\\n  {j}. [{formula['confidence']:.2f}] {formula['name']}")
                print(f"     Formula: {formula['formula']}")
                print(f"     Type: {formula['type']}")
                print(f"     Description: {formula['description']}")
                if formula.get('context'):
                    print(f"     Context: {formula['context'][:100]}...")
        else:
            print("❌ No formulas found")
        
        # Store result
        result = {
            "title": sample['title'],
            "content_length": len(sample['content']),
            "formulas": formulas,
            "total_formulas": len(formulas)
        }
        all_results.append(result)
    
    # Summary
    successful = len([r for r in all_results if r['total_formulas'] > 0])
    
    print(f"\\n{'='*70}")
    print(f"📊 DEMO SUMMARY")
    print(f"{'='*70}")
    print(f"Documents processed: {len(all_results)}")
    print(f"Successful extractions: {successful} ({successful/len(all_results)*100:.1f}%)")
    print(f"Total formulas found: {total_formulas}")
    print(f"Average formulas per document: {total_formulas/len(all_results):.1f}")
    
    # Analyze by type
    type_counts = {}
    all_formulas = []
    
    for result in all_results:
        for formula in result['formulas']:
            formula_type = formula.get('type', 'unknown')
            type_counts[formula_type] = type_counts.get(formula_type, 0) + 1
            formula['source_title'] = result['title']
            all_formulas.append(formula)
    
    if type_counts:
        print(f"\\n📋 FORMULA TYPES:")
        for formula_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {formula_type}: {count} formulas")
    
    # Top formulas
    if all_formulas:
        print(f"\\n🏆 TOP FORMULAS BY CONFIDENCE:")
        all_formulas.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        for i, formula in enumerate(all_formulas[:15], 1):
            print(f"{i:2d}. [{formula.get('confidence', 0):.2f}] {formula['name'][:50]}")
            print(f"     {formula['formula'][:80]}...")
            print(f"     Type: {formula.get('type', 'unknown')}")
            print()
    
    # Save demo results
    output_file = Path("data/demo_formula_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "demo_summary": {
                "total_documents": len(all_results),
                "successful_extractions": successful,
                "total_formulas": total_formulas,
                "success_rate": f"{successful/len(all_results)*100:.1f}%",
                "formula_types": type_counts
            },
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Demo results saved to: {output_file}")
    
    return total_formulas > 0

def test_individual_patterns():
    """Test từng pattern riêng lẻ"""
    
    print("\\n🧪 TESTING INDIVIDUAL PATTERNS")
    print("=" * 50)
    
    extractor = FinalFormulaExtractor()
    
    test_cases = [
        ("Mức lương cơ bản = 1.800.000 đồng/tháng", "amount_definition"),
        ("Tỷ lệ thuế thu nhập cá nhân: 10%", "percentage_rate"),
        ("Thuế suất: 15%", "tax_rate"),
        ("Phụ cấp trách nhiệm = 20% × lương cơ bản", "allowance"),
        ("Bảo hiểm xã hội = 8% mức lương", "insurance_rate"),
        ("Lệ phí cấp giấy phép: 135.000 đồng", "fee"),
        ("Từ 500.000 đến 1.000.000 đồng", "money_range"),
        ("Không quá 2.000.000 đồng", "money_limit"),
        ("Giảm trừ gia cảnh: 11.000.000 đồng/tháng", "deduction"),
        ("Mức phạt: 500.000 đồng", "penalty")
    ]
    
    successful_patterns = 0
    
    for i, (test_text, expected_type) in enumerate(test_cases, 1):
        print(f"\\n{i:2d}. Test: {test_text}")
        
        formulas = extractor.extract_formulas_from_text(test_text)
        
        if formulas:
            successful_patterns += 1
            best_formula = formulas[0]  # Highest confidence
            print(f"    ✅ MATCH: [{best_formula['confidence']:.2f}] {best_formula['name']}")
            print(f"       Type: {best_formula['type']} (expected: {expected_type})")
            print(f"       Formula: {best_formula['formula']}")
        else:
            print(f"    ❌ NO MATCH")
    
    print(f"\\n📊 Pattern Test Summary: {successful_patterns}/{len(test_cases)} patterns working ({successful_patterns/len(test_cases)*100:.1f}%)")
    
    return successful_patterns

if __name__ == "__main__":
    print("🚀 FORMULA EXTRACTION DEMO")
    print("=" * 80)
    
    # Test individual patterns first
    pattern_success = test_individual_patterns()
    
    # Then test with full content
    content_success = demo_with_sample_content()
    
    print(f"\\n{'='*80}")
    print(f"🎯 OVERALL DEMO RESULTS")
    print(f"{'='*80}")
    print(f"✅ Pattern tests: {'PASSED' if pattern_success > 5 else 'FAILED'}")
    print(f"✅ Content extraction: {'PASSED' if content_success else 'FAILED'}")
    print(f"🎉 Demo status: {'SUCCESS' if (pattern_success > 5 and content_success) else 'NEEDS IMPROVEMENT'}")
    print(f"{'='*80}")
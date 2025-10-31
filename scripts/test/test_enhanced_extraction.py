#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Enhanced Formula Extraction với dữ liệu thực"""
import json
import asyncio
from pathlib import Path
from scripts.extract.enhanced_formula_extractor import EnhancedFormulaExtractor
from smart_formula_patterns import SmartFormulaPatterns
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_with_real_data():
    """Test với dữ liệu thực từ file"""
    
    # Test data - một số URL có khả năng chứa công thức
    test_links = [
        {
            "Stt": 1,
            "Tên văn bản": "Thông tư 30/2016/TT-BTC hướng dẫn thuế thu nhập cá nhân",
            "Url": "https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-30-2016-TT-BTC-huong-dan-thuc-hien-mot-so-dieu-cua-Luat-Thue-thu-nhap-ca-nhan-309144.aspx"
        },
        {
            "Stt": 2,
            "Tên văn bản": "Nghị định 38/2019/NĐ-CP về bảo hiểm xã hội",
            "Url": "https://thuvienphapluat.vn/van-ban/Bao-hiem/Nghi-dinh-38-2019-ND-CP-quy-dinh-ve-bao-hiem-xa-hoi-415578.aspx"
        }
    ]
    
    print("🧪 TESTING ENHANCED FORMULA EXTRACTION")
    print("=" * 60)
    
    # Test 1: Smart Patterns với text mẫu
    print("\n1️⃣ Testing Smart Patterns with sample text:")
    patterns = SmartFormulaPatterns()
    
    sample_texts = [
        """
        Mức lương cơ bản áp dụng chung = 1.800.000 đồng/tháng.
        Tỷ lệ thuế thu nhập cá nhân: 10% đối với thu nhập từ 5 triệu đến 10 triệu đồng.
        Phụ cấp trách nhiệm được tính bằng 20% × lương cơ bản.
        Thuế thu nhập = thu nhập chịu thuế × tỷ lệ thuế.
        Tiền phạt vi phạm hành chính từ 500.000 đến 2.000.000 đồng.
        """,
        """
        Mức trợ cấp xã hội không quá 1.560.000 đồng/tháng.
        Lương hưu = lương cơ bản × tỷ lệ hưu × hệ số điều chỉnh.
        Bảo hiểm y tế = 4.5% × mức lương đóng bảo hiểm.
        Phí dịch vụ công được tính theo công thức: Phí = giá trị dịch vụ × 0.5%.
        """
    ]
    
    for i, text in enumerate(sample_texts, 1):
        print(f"\n📝 Sample {i}:")
        results = patterns.extract_with_patterns(text)
        
        if results:
            print(f"   ✅ Found {len(results)} formulas:")
            for j, result in enumerate(results[:3], 1):  # Show top 3
                print(f"   {j}. [{result['confidence']:.2f}] {result['name']}")
                print(f"      Formula: {result['formula']}")
                print(f"      Type: {result['type']}")
        else:
            print("   ❌ No formulas found")
    
    # Test 2: Enhanced Extractor với URL thực
    print(f"\n2️⃣ Testing Enhanced Extractor with real URLs:")
    
    from playwright.async_api import async_playwright
    
    extractor = EnhancedFormulaExtractor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Load cookies if available
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
            print("   🍪 Using saved cookies")
        
        context = await browser.new_context(**context_options)
        
        for item in test_links:
            url = item["Url"]
            title = item["Tên văn bản"]
            
            print(f"\n📄 Testing: {title}")
            print(f"   URL: {url}")
            
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                
                result = await extractor.extract_from_page(page, url)
                
                formulas_count = result.get("total_formulas", 0)
                if formulas_count > 0:
                    print(f"   ✅ Found {formulas_count} formulas:")
                    
                    # Show details
                    for i, formula in enumerate(result["formulas"][:3], 1):
                        print(f"   {i}. [{formula.get('confidence', 0):.2f}] {formula['name']}")
                        print(f"      Formula: {formula['formula'][:100]}...")
                        print(f"      Type: {formula.get('type', 'unknown')}")
                        if formula.get('context'):
                            print(f"      Context: {formula['context'][:80]}...")
                else:
                    print(f"   ❌ No formulas found")
                    if result.get('error'):
                        print(f"   Error: {result['error']}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await page.close()
        
        await browser.close()
    
    print(f"\n{'='*60}")
    print("🎯 Test completed!")

def test_patterns_only():
    """Test chỉ patterns mà không cần browser"""
    print("🧪 TESTING SMART PATTERNS ONLY")
    print("=" * 50)
    
    patterns = SmartFormulaPatterns()
    
    # Test với các ví dụ thực tế từ văn bản pháp luật
    real_examples = [
        # Từ Thông tư thuế
        """
        Mức giảm trừ gia cảnh cho người nộp thuế là 11.000.000 đồng/tháng.
        Mức giảm trừ gia cảnh cho mỗi người phụ thuộc là 4.400.000 đồng/tháng.
        Thuế thu nhập cá nhân phải nộp = Thu nhập tính thuế × Thuế suất.
        """,
        
        # Từ Nghị định bảo hiểm
        """
        Mức đóng bảo hiểm xã hội bằng 8% mức lương đóng bảo hiểm xã hội.
        Mức đóng bảo hiểm y tế bằng 1,5% mức lương đóng bảo hiểm y tế.
        Mức lương tối thiểu vùng I là 4.680.000 đồng/tháng.
        """,
        
        # Từ Nghị định lương
        """
        Lương cơ sở áp dụng chung là 1.800.000 đồng/tháng.
        Phụ cấp trách nhiệm = Hệ số phụ cấp × Lương cơ sở.
        Phụ cấp thâm niên nghề = Tỷ lệ phụ cấp × Lương cơ sở × Số năm công tác.
        """,
        
        # Từ Thông tư phí lệ phí
        """
        Lệ phí cấp giấy phép lái xe hạng A1: 135.000 đồng.
        Lệ phí cấp giấy phép lái xe hạng B1: 270.000 đồng.
        Phí sát hạch lái xe = Phí cơ bản + Phí sát hạch thực hành.
        """,
        
        # Từ Nghị định xử phạt
        """
        Mức phạt tiền từ 800.000 đồng đến 1.200.000 đồng.
        Tiền phạt không quá 3 lần mức lương cơ sở.
        Phạt bổ sung = 10% × Giá trị hàng hóa vi phạm.
        """
    ]
    
    total_found = 0
    
    for i, example in enumerate(real_examples, 1):
        print(f"\n📝 Example {i}:")
        print(f"Text: {example.strip()[:100]}...")
        
        results = patterns.extract_with_patterns(example)
        
        if results:
            print(f"   ✅ Found {len(results)} formulas:")
            total_found += len(results)
            
            for j, result in enumerate(results, 1):
                print(f"   {j}. [{result['confidence']:.2f}] {result['name']}")
                print(f"      Formula: {result['formula']}")
                print(f"      Type: {result['type']}")
                if result.get('components'):
                    print(f"      Components: {result['components']}")
        else:
            print("   ❌ No formulas found")
    
    print(f"\n{'='*50}")
    print(f"🎯 SUMMARY: Found {total_found} formulas total")
    print(f"📊 Average: {total_found/len(real_examples):.1f} formulas per example")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Enhanced Formula Extraction")
    parser.add_argument("--patterns-only", action="store_true", 
                       help="Test only patterns without browser")
    
    args = parser.parse_args()
    
    if args.patterns_only:
        test_patterns_only()
    else:
        asyncio.run(test_with_real_data())
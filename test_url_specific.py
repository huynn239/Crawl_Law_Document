#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test URL Specific - Test với URL cụ thể"""
import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from core.extractors.production_extractor import ProductionReadyExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

def test_url_crawl():
    """Test crawl URL cụ thể"""
    
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx?dll=true"
    
    print("TEST URL CRAWL")
    print("=" * 60)
    print(f"URL: {url}")
    
    try:
        # Headers để giả lập browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print("\n1. CRAWLING...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"   Content-Length: {len(response.content):,} bytes")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm nội dung chính
        content_selectors = [
            '.content1',
            '.noidung1',
            '.fulltext',
            '.content',
            '#content1',
            '.document-content',
            '.main-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element.get_text(strip=True)
                print(f"   Found content with selector: {selector}")
                break
        
        if not main_content:
            # Fallback: lấy toàn bộ text
            main_content = soup.get_text(strip=True)
            print("   Using full page text as fallback")
        
        print(f"   Extracted text length: {len(main_content):,} chars")
        
        # Lưu raw content
        os.makedirs("data", exist_ok=True)
        with open("data/test_url_raw_content.txt", "w", encoding="utf-8") as f:
            f.write(main_content)
        
        print("\n2. EXTRACTION...")
        extractor = ProductionReadyExtractor()
        result = extractor.extract_from_text(main_content)
        
        print(f"   Formulas: {result['total_formulas']}")
        print(f"   Parameters: {result['total_parameters']}")
        print(f"   Method: {result['extraction_method']}")
        
        # Hiển thị top results
        if result['total_formulas'] > 0:
            print(f"\n   TOP FORMULAS:")
            for i, formula in enumerate(result['formulas'][:3], 1):
                print(f"   {i}. [{formula['confidence']:.2f}] {formula['name']}")
                print(f"      {formula['formula'][:100]}...")
        
        if result['total_parameters'] > 0:
            print(f"\n   TOP PARAMETERS:")
            for i, param in enumerate(result['parameters'][:3], 1):
                print(f"   {i}. [{param['confidence']:.2f}] {param['name']}")
                print(f"      {param.get('value', param.get('formula', ''))[:80]}...")
        
        # Lưu kết quả
        with open("data/test_url_extraction_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n3. ASSESSMENT:")
        
        # Đánh giá chất lượng
        quality_score = 0
        
        if result['total_formulas'] >= 5:
            quality_score += 30
            print(f"   ✓ Good formula count: {result['total_formulas']}")
        elif result['total_formulas'] >= 2:
            quality_score += 15
            print(f"   ~ Moderate formula count: {result['total_formulas']}")
        else:
            print(f"   ✗ Low formula count: {result['total_formulas']}")
        
        if result['total_parameters'] >= 10:
            quality_score += 30
            print(f"   ✓ Good parameter count: {result['total_parameters']}")
        elif result['total_parameters'] >= 5:
            quality_score += 15
            print(f"   ~ Moderate parameter count: {result['total_parameters']}")
        else:
            print(f"   ✗ Low parameter count: {result['total_parameters']}")
        
        # Kiểm tra confidence
        if result['formulas']:
            avg_confidence = sum(f['confidence'] for f in result['formulas']) / len(result['formulas'])
            if avg_confidence >= 0.7:
                quality_score += 25
                print(f"   ✓ High confidence: {avg_confidence:.2f}")
            elif avg_confidence >= 0.5:
                quality_score += 15
                print(f"   ~ Moderate confidence: {avg_confidence:.2f}")
            else:
                print(f"   ✗ Low confidence: {avg_confidence:.2f}")
        
        # Kiểm tra có công thức lương không
        salary_keywords = ['lương', 'tiền', 'mức', 'phụ cấp', 'bảo hiểm', 'thuế']
        salary_formulas = []
        for formula in result['formulas']:
            if any(keyword in formula['name'].lower() or keyword in formula['formula'].lower() 
                   for keyword in salary_keywords):
                salary_formulas.append(formula)
        
        if salary_formulas:
            quality_score += 15
            print(f"   ✓ Found salary-related formulas: {len(salary_formulas)}")
        
        print(f"\n   OVERALL QUALITY SCORE: {quality_score}/100")
        
        if quality_score >= 70:
            print("   🎉 EXCELLENT - Regex patterns work well!")
        elif quality_score >= 50:
            print("   👍 GOOD - Minor improvements needed")
        elif quality_score >= 30:
            print("   ⚠️  MODERATE - Significant improvements needed")
        else:
            print("   ❌ POOR - Major regex updates required")
        
        # Recommendations
        print(f"\n4. RECOMMENDATIONS:")
        
        if result['total_formulas'] < 5:
            print("   • Update formula regex patterns to catch more variations")
        
        if result['total_parameters'] < 10:
            print("   • Enhance parameter detection patterns")
        
        if result['formulas'] and sum(f['confidence'] for f in result['formulas']) / len(result['formulas']) < 0.6:
            print("   • Improve confidence scoring algorithm")
        
        if not salary_formulas:
            print("   • Add specific patterns for salary/financial calculations")
        
        print(f"\nFiles saved:")
        print(f"   - Raw content: data/test_url_raw_content.txt")
        print(f"   - Extraction result: data/test_url_extraction_result.json")
        
        return result
        
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_url_crawl()
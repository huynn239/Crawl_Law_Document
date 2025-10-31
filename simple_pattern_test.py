#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple pattern test"""
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_basic_patterns():
    """Test basic formula patterns"""
    
    # Test cases
    test_cases = [
        "Muc luong co ban = 1.800.000 dong/thang",
        "Ty le thue: 10%",
        "Phu cap = 20% x luong co ban",
        "Le phi: 135.000 dong",
        "Tu 500.000 den 1.000.000 dong"
    ]
    
    # Simple patterns
    patterns = [
        {
            'name': 'Muc = so dong',
            'pattern': r'(muc\s+[^=]+)\s*=\s*([\d.,]+)\s*(dong)',
        },
        {
            'name': 'Ty le: so%',
            'pattern': r'(ty\s*le[^:]*)\s*:\s*([\d.,]+\s*%)',
        },
        {
            'name': 'Phep nhan voi %',
            'pattern': r'([^=]+)\s*=\s*([\d.,]+\s*%)\s*[x*]\s*([^.]+)',
        },
        {
            'name': 'Le phi: so dong',
            'pattern': r'(le\s*phi[^:]*)\s*:\s*([\d.,]+)\s*(dong)',
        },
        {
            'name': 'Tu so den so dong',
            'pattern': r'tu\s*([\d.,]+)\s*den\s*([\d.,]+)\s*(dong)',
        }
    ]
    
    print("Testing Basic Patterns")
    print("=" * 50)
    
    total_matches = 0
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{i}. Test: {test_text}")
        
        found_match = False
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            matches = list(re.finditer(pattern, test_text, re.IGNORECASE))
            
            if matches:
                found_match = True
                total_matches += len(matches)
                print(f"   MATCH ({pattern_info['name']}): {matches[0].group(0)}")
                print(f"   Groups: {matches[0].groups()}")
                break
        
        if not found_match:
            print("   No match found")
    
    print(f"\nSummary: {total_matches} total matches found")
    return total_matches

def test_money_patterns():
    """Test money amount patterns"""
    
    money_texts = [
        "1.800.000 dong",
        "1,800,000 dong", 
        "135.000 dong",
        "2.5 trieu dong",
        "1.5 ty dong"
    ]
    
    money_pattern = r'[\d.,]+\s*(?:trieu|ty)?\s*dong'
    
    print("\nTesting Money Patterns")
    print("=" * 30)
    
    matches_found = 0
    
    for text in money_texts:
        matches = list(re.finditer(money_pattern, text, re.IGNORECASE))
        if matches:
            matches_found += 1
            print(f"MATCH: {text} -> {matches[0].group(0)}")
        else:
            print(f"NO MATCH: {text}")
    
    print(f"\nMoney patterns: {matches_found}/{len(money_texts)} matched")
    return matches_found

def test_percentage_patterns():
    """Test percentage patterns"""
    
    percentage_texts = [
        "10%",
        "15 %",
        "20 phan tram",
        "5.5%",
        "0.5 phan tram"
    ]
    
    percentage_pattern = r'[\d.,]+\s*(?:%|phan\s*tram)'
    
    print("\nTesting Percentage Patterns")
    print("=" * 35)
    
    matches_found = 0
    
    for text in percentage_texts:
        matches = list(re.finditer(percentage_pattern, text, re.IGNORECASE))
        if matches:
            matches_found += 1
            print(f"MATCH: {text} -> {matches[0].group(0)}")
        else:
            print(f"NO MATCH: {text}")
    
    print(f"\nPercentage patterns: {matches_found}/{len(percentage_texts)} matched")
    return matches_found

if __name__ == "__main__":
    print("SIMPLE PATTERN TEST")
    print("=" * 60)
    
    basic_matches = test_basic_patterns()
    money_matches = test_money_patterns()
    percentage_matches = test_percentage_patterns()
    
    print(f"\n" + "=" * 60)
    print("FINAL SUMMARY")
    print(f"Basic formula patterns: {basic_matches} matches")
    print(f"Money patterns: {money_matches} matches") 
    print(f"Percentage patterns: {percentage_matches} matches")
    print(f"Total: {basic_matches + money_matches + percentage_matches} matches")
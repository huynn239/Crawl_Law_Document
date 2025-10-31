#!/usr/bin/env python3
import json
import os

def show_results():
    with open('data/adaptive_thongtu21_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("THONG TU 21/2025 - SALARY CALCULATION FORMULAS")
    print("=" * 60)
    print(f"Total Formulas: {data.get('total_formulas', 0)}")
    print(f"Total Parameters: {data.get('total_parameters', 0)}")
    print(f"Domain: {data.get('detected_domain', 'unknown')}")
    
    print("\nKEY SALARY FORMULAS:")
    print("-" * 40)
    
    # Show main salary formulas
    salary_formulas = [f for f in data['formulas'] if f['type'] in ['salary_per_lesson', 'salary_calc']]
    
    for i, formula in enumerate(salary_formulas[:4], 1):
        print(f"\n{i}. Type: {formula.get('type', 'unknown')}")
        # Clean formula text
        formula_text = formula.get('formula', '').encode('ascii', 'replace').decode('ascii')
        formula_text = formula_text.replace('|', '')
        if len(formula_text) > 100:
            formula_text = formula_text[:100] + "..."
        print(f"   Formula: {formula_text}")
        print(f"   Confidence: {formula.get('confidence', 0)}")
    
    print("\nMAIN CALCULATION RULES:")
    print("-" * 40)
    print("1. For K-12 teachers:")
    print("   Salary per lesson = (Total 12-month salary / Annual lesson quota) x (Teaching weeks / 52)")
    
    print("\n2. For university teachers:")
    print("   Salary per lesson = (Total 12-month salary / Annual lesson quota) x (Admin hours / 1760) x (44/52)")
    
    print("\n3. Extra teaching salary:")
    print("   Extra salary = Extra lessons x Salary per extra lesson")
    
    print("\nLIMITS:")
    print("-" * 40)
    print("- Max extra lessons: 200 lessons/year")
    print("- Min basic salary: 1,800,000 VND/month")

if __name__ == "__main__":
    show_results()
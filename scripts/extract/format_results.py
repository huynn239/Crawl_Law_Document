#!/usr/bin/env python3
"""
Format the adaptive extraction results for better readability
"""

import json
import os

def format_adaptive_results():
    """Format and display the adaptive extraction results"""
    
    # Read the results file
    results_file = 'data/adaptive_thongtu21_result.json'
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("THONG TU 21/2025 - TIEN LUONG DAY THEM GIO")
    print("=" * 80)
    
    print(f"URL: {data.get('url', 'N/A')}")
    print(f"Detected Domain: {data.get('detected_domain', 'unknown')}")
    print(f"Extraction Method: {data.get('extraction_method', 'unknown')}")
    print(f"Content Length: {data.get('content_length', 0)} characters")
    print(f"Total Formulas: {data.get('total_formulas', 0)}")
    print(f"Total Parameters: {data.get('total_parameters', 0)}")
    
    print("\n" + "=" * 80)
    print("CONG THUC TINH TOAN (FORMULAS)")
    print("=" * 80)
    
    formulas = data.get('formulas', [])
    
    # Group formulas by type
    formula_groups = {}
    for formula in formulas:
        formula_type = formula.get('type', 'unknown')
        if formula_type not in formula_groups:
            formula_groups[formula_type] = []
        formula_groups[formula_type].append(formula)
    
    for formula_type, group_formulas in formula_groups.items():
        print(f"\n--- {formula_type.upper().replace('_', ' ')} ({len(group_formulas)} formulas) ---")
        
        for i, formula in enumerate(group_formulas, 1):
            print(f"\n{i}. {formula.get('name', 'N/A')}")
            print(f"   Confidence: {formula.get('confidence', 0):.2f}")
            
            # Clean and display formula
            formula_text = formula.get('formula', '')
            if len(formula_text) > 200:
                formula_text = formula_text[:200] + "..."
            print(f"   Formula: {formula_text}")
            
            # Display context
            context = formula.get('context', '')
            if context and len(context) > 150:
                context = context[:150] + "..."
            if context:
                print(f"   Context: {context}")
    
    print("\n" + "=" * 80)
    print("THAM SO VA GIA TRI (PARAMETERS)")
    print("=" * 80)
    
    parameters = data.get('parameters', [])
    if parameters:
        for i, param in enumerate(parameters, 1):
            print(f"\n{i}. {param.get('name', 'N/A')}")
            print(f"   Value: {param.get('value', 'N/A')}")
            print(f"   Type: {param.get('type', 'unknown')}")
            print(f"   Confidence: {param.get('confidence', 0):.2f}")
            print(f"   Full Text: {param.get('full_text', 'N/A')}")
    else:
        print("No parameters found")
    
    print("\n" + "=" * 80)
    print("KEY SALARY FORMULAS (CLEANED)")
    print("=" * 80)
    
    # Extract and clean key salary formulas
    key_formulas = []
    for formula in formulas:
        if formula.get('type') in ['salary_per_lesson', 'salary_calc'] and formula.get('confidence', 0) >= 0.9:
            key_formulas.append(formula)
    
    if key_formulas:
        for i, formula in enumerate(key_formulas[:5], 1):  # Show top 5
            print(f"\n{i}. SALARY CALCULATION:")
            
            # Try to extract the core formula
            formula_text = formula.get('formula', '')
            
            # Look for the main equation pattern
            if '=' in formula_text:
                parts = formula_text.split('=', 1)
                left_side = parts[0].strip()
                right_side = parts[1].strip()
                
                # Clean up the sides
                if '|' in left_side:
                    left_side = left_side.split('|')[0].strip()
                if '|' in right_side:
                    right_side = right_side.split('|')[0].strip()
                
                print(f"   {left_side} = {right_side}")
            else:
                print(f"   {formula_text[:100]}...")
            
            print(f"   Confidence: {formula.get('confidence', 0):.2f}")
    else:
        print("No key salary formulas found with high confidence")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    format_adaptive_results()
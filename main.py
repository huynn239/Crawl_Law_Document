#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main entry point for thuvienphapluat-crawler"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.extractors.production_extractor import ProductionReadyExtractor

def main():
    """Main function"""
    print("Thuvienphapluat Crawler")
    print("Available commands:")
    print("  python scripts/crawl/crawl_formulas.py - Crawl formulas")
    print("  python scripts/utils/setup_db.py - Setup database")
    
    # Example usage
    extractor = ProductionReadyExtractor()
    sample_text = "Tiền lương = Hệ số × 1.800.000 đồng"
    result = extractor.extract_from_text(sample_text)
    print(f"Sample extraction: {result['total_formulas']} formulas found")

if __name__ == "__main__":
    main()

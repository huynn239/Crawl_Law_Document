#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Document Filter - Pre-filtering for documents"""
import re

class DocumentFilter:
    def __init__(self):
        self.formula_indicators = [r'=', r'×|÷|\*|/|%', r'[0-9.,]+\s*%', r'[0-9.,]+\s*đồng']
        self.exclude_patterns = [r'^\s*điều\s+\d+', r'liên hệ|email|website']
    
    def has_formulas(self, content: str) -> bool:
        if not content or len(content) < 50:
            return False
        indicator_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in self.formula_indicators)
        exclusion_count = sum(1 for p in self.exclude_patterns if re.search(p, content, re.IGNORECASE))
        return (indicator_count - exclusion_count * 2) >= 1

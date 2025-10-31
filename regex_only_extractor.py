#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regex Only Extractor - Hệ thống A chỉ dùng Regex patterns"""
import sys
import os
from typing import Dict
from playwright.async_api import async_playwright
from pathlib import Path
from production_ready_extractor import ProductionReadyExtractor

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

class RegexOnlyExtractor:
    def __init__(self):
        self.extractor = ProductionReadyExtractor()
    
    async def extract_from_url(self, url: str) -> Dict:
        """Trích xuất chỉ bằng Regex patterns, không dùng LLM"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Load cookies if available
            context_options = {}
            cookies_path = Path("data/cookies.json")
            if cookies_path.exists():
                context_options["storage_state"] = str(cookies_path)
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Click tab nội dung
                for selector in ["#aNoiDung", "a[href='#tab1']"]:
                    try:
                        await page.click(selector, timeout=2000)
                        await page.wait_for_timeout(2000)
                        break
                    except:
                        continue
                
                # Get content
                content = ""
                try:
                    element = await page.query_selector("#tab1")
                    if element:
                        content = await element.inner_text()
                    else:
                        content = await page.inner_text("body")
                except:
                    content = await page.inner_text("body")
                
                # Extract using ONLY regex patterns
                result = self.extractor.extract_from_text(content)
                result['url'] = url
                result['extraction_method'] = 'regex_only_system_a'
                
                return result
                
            except Exception as e:
                return {
                    'url': url,
                    'error': str(e),
                    'formulas': [],
                    'parameters': [],
                    'total_formulas': 0,
                    'total_parameters': 0,
                    'extraction_method': 'regex_only_system_a_failed'
                }
            finally:
                await browser.close()
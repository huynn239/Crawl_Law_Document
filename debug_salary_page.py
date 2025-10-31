#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug trang lương giáo viên"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from simple_formula_extractor import SimpleFormulaExtractor
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def debug_salary_page():
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            print(f"Loading: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            title = await page.title()
            print(f"Title: {title}")
            
            # Click tab nội dung
            for selector in ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')"]:
                try:
                    await page.click(selector, timeout=2000)
                    print(f"Clicked: {selector}")
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy nội dung
            content = ""
            try:
                element = await page.query_selector("#tab1")
                if element:
                    content = await element.inner_text()
                    print(f"Tab1 content length: {len(content)}")
                else:
                    content = await page.inner_text("body")
                    print(f"Body content length: {len(content)}")
            except:
                content = await page.inner_text("body")
                print(f"Fallback body content length: {len(content)}")
            
            # Hiển thị sample content
            if content:
                lines = content.split('\n')
                print(f"\nSample content (first 20 lines):")
                for i, line in enumerate(lines[:20], 1):
                    if line.strip():
                        print(f"{i:2d}. {line.strip()[:100]}")
                
                # Tìm các dòng có từ khóa liên quan đến lương
                salary_lines = []
                for line in lines:
                    line = line.strip()
                    if (len(line) > 10 and 
                        any(keyword in line.lower() for keyword in 
                            ['lương', 'tiền', 'mức', 'tỷ lệ', 'phụ cấp', 'đồng', '%']) and
                        any(char.isdigit() for char in line)):
                        salary_lines.append(line)
                
                if salary_lines:
                    print(f"\nFound {len(salary_lines)} lines with salary keywords:")
                    for i, line in enumerate(salary_lines[:10], 1):
                        print(f"{i:2d}. {line[:120]}")
                else:
                    print("\nNo lines with salary keywords found")
                
                # Test với extractor
                extractor = SimpleFormulaExtractor()
                formulas = extractor.extract_formulas(content)
                
                if formulas:
                    print(f"\nExtractor found {len(formulas)} formulas:")
                    for i, formula in enumerate(formulas, 1):
                        print(f"{i}. [{formula['confidence']:.2f}] {formula['name']}")
                        print(f"   Formula: {formula['formula']}")
                        print(f"   Type: {formula['type']}")
                else:
                    print("\nExtractor found no formulas")
            
            # Chờ để quan sát
            print(f"\nWaiting 10 seconds for inspection...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_salary_page())
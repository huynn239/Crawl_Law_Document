#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug page content để xem nội dung thực tế"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def debug_page_content():
    """Debug nội dung trang để hiểu cấu trúc"""
    
    # URL test
    url = "https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-30-2016-TT-BTC-huong-dan-thuc-hien-mot-so-dieu-cua-Luat-Thue-thu-nhap-ca-nhan-309144.aspx"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Hiển thị browser để debug
        
        # Load cookies if available
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
            print("Using saved cookies")
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            print(f"Loading page: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Lấy title
            title = await page.title()
            print(f"Page title: {title}")
            
            # Kiểm tra các tab có sẵn
            print("\nChecking available tabs:")
            tab_selectors = [
                "#aNoiDung",
                "a[href='#tab1']", 
                "a:has-text('Nội dung')",
                "#tab1",
                ".tab-content",
                "[role='tabpanel']"
            ]
            
            for selector in tab_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        print(f"  {selector}: Found ({len(text)} chars)")
                        if len(text) > 0:
                            print(f"    Sample: {text[:100]}...")
                    else:
                        print(f"  {selector}: Not found")
                except Exception as e:
                    print(f"  {selector}: Error - {e}")
            
            # Thử click tab nội dung
            print(f"\nTrying to click content tab...")
            clicked = False
            for selector in ["#aNoiDung", "a[href='#tab1']", "a:has-text('Nội dung')"]:
                try:
                    await page.click(selector, timeout=2000)
                    print(f"  Clicked: {selector}")
                    clicked = True
                    break
                except:
                    print(f"  Failed to click: {selector}")
            
            if not clicked:
                print("  Using hash navigation...")
                await page.evaluate("() => { location.hash = '#tab1'; }")
            
            await page.wait_for_timeout(3000)
            
            # Lấy nội dung sau khi click
            print(f"\nGetting content after tab click:")
            
            # Thử nhiều cách lấy nội dung
            content_methods = [
                ("#tab1", "Tab1 content"),
                ("#tab1 .tab-pane", "Tab1 pane content"),
                (".tab-content", "Tab content area"),
                ("body", "Full body content")
            ]
            
            for selector, description in content_methods:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        print(f"  {description}: {len(content)} chars")
                        
                        if len(content) > 100:
                            # Tìm các đoạn có số và từ khóa liên quan đến công thức
                            lines = content.split('\n')
                            formula_lines = []
                            
                            for line in lines:
                                line = line.strip()
                                if (len(line) > 10 and 
                                    any(char.isdigit() for char in line) and
                                    any(keyword in line.lower() for keyword in 
                                        ['mức', 'tỷ lệ', 'thuế', 'phí', 'lương', 'bằng', 'tính', '=', '%', 'đồng'])):
                                    formula_lines.append(line)
                            
                            if formula_lines:
                                print(f"    Potential formula lines found: {len(formula_lines)}")
                                for i, line in enumerate(formula_lines[:5], 1):
                                    print(f"      {i}. {line[:100]}...")
                            else:
                                print(f"    No potential formula lines found")
                                # Show sample content
                                print(f"    Sample content: {content[:300]}...")
                        
                except Exception as e:
                    print(f"  {description}: Error - {e}")
            
            # Chờ để có thể quan sát browser
            print(f"\nWaiting 10 seconds for manual inspection...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page_content())
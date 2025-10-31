#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đọc toàn bộ nội dung văn bản"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def read_full_content():
    url = "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-21-2025-TT-BGDDT-che-do-tra-tien-luong-day-them-gio-nha-giao-trong-cac-co-so-giao-duc-cong-lap-673797.aspx"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        context_options = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            context_options["storage_state"] = str(cookies_path)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Click tab nội dung
            for selector in ["#aNoiDung", "a[href='#tab1']"]:
                try:
                    await page.click(selector, timeout=2000)
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue
            
            # Lấy toàn bộ nội dung
            content = ""
            try:
                element = await page.query_selector("#tab1")
                if element:
                    content = await element.inner_text()
                else:
                    content = await page.inner_text("body")
            except:
                content = await page.inner_text("body")
            
            print(f"📄 TOÀN BỘ NỘI DUNG VĂN BẢN")
            print(f"📏 Độ dài: {len(content)} ký tự")
            print("=" * 80)
            
            # Hiển thị toàn bộ nội dung
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip():
                    print(f"{i:3d}. {line.strip()}")
            
            print("=" * 80)
            print(f"📊 Tổng cộng: {len([l for l in lines if l.strip()])} dòng có nội dung")
            
            # Lưu vào file
            output_file = Path("data/full_content.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"💾 Đã lưu vào: {output_file}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(read_full_content())
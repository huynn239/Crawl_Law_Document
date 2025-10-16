# Debug extract - lưu HTML và test logic
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json
import sys

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/storage_state.json")
        page = await context.new_page()
        
        url = "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Van-ban-hop-nhat-17-VBHN-BXD-2025-Nghi-dinh-dang-ky-quoc-tich-va-dang-ky-cac-quyen-doi-voi-tau-bay-676614.aspx"
        
        await page.goto(url)
        await page.wait_for_timeout(2000)
        
        # Click tab4
        await page.click("#aLuocDo")
        await page.wait_for_timeout(2000)
        
        # Lưu HTML
        html = await page.locator("#tab4").inner_html()
        Path("debug_tab4.html").write_text(html, encoding="utf-8")
        print("Da luu debug_tab4.html")
        
        # Test extract
        from tvpl_crawler.playwright_extract_simple import extract_tab4_simple_async
        result = await extract_tab4_simple_async(page)
        
        # Write result to file
        Path("debug_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== KET QUA EXTRACT ===")
        print(f"Relations found: {len(result.get('tab4_relations', {}))}")
        print(f"Total links: {result.get('tab4_total_relations', 0)}")
        for key, val in result.get('tab4_summary', {}).items():
            print(f"  {key}: {val}")
        
        await browser.close()

asyncio.run(main())

# Debug TNPL page structure
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/storage_state.json")
        page = await context.new_page()
        
        url = "https://thuvienphapluat.vn/tnpl/"
        print(f"Loading: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            print("Timeout, but continuing...")
        await page.wait_for_timeout(5000)
        
        # Save full HTML
        html = await page.content()
        Path("debug_tnpl_full.html").write_text(html, encoding="utf-8")
        print("Saved: debug_tnpl_full.html")
        
        # Get page title
        title = await page.title()
        Path("debug_tnpl_info.txt").write_text(f"Title: {title}\n", encoding="utf-8")
        
        # Find main content areas
        info = "\n=== Main containers ===\n"
        containers = await page.query_selector_all("div[class*='content'], div[id*='content'], main, article")
        info += f"Found {len(containers)} content containers\n"
        
        # Find search/filter forms
        info += "\n=== Forms ===\n"
        forms = await page.query_selector_all("form")
        for i, form in enumerate(forms):
            form_id = await form.get_attribute("id")
            form_class = await form.get_attribute("class")
            info += f"Form {i+1}: id={form_id}, class={form_class}\n"
        
        # Find tables
        info += "\n=== Tables ===\n"
        tables = await page.query_selector_all("table")
        for i, table in enumerate(tables):
            table_id = await table.get_attribute("id")
            table_class = await table.get_attribute("class")
            rows = await table.query_selector_all("tr")
            info += f"Table {i+1}: id={table_id}, class={table_class}, rows={len(rows)}\n"
        
        # Find links
        info += "\n=== Links (first 10) ===\n"
        links = await page.query_selector_all("a[href*='tnpl']")
        for i, link in enumerate(links[:10]):
            href = await link.get_attribute("href")
            text = await link.inner_text()
            info += f"{i+1}. {text[:50]} -> {href}\n"
        
        Path("debug_tnpl_info.txt").write_text(info, encoding="utf-8")
        
        # Screenshot
        await page.screenshot(path="debug_tnpl_screenshot.png", full_page=True)
        print("Done! Check debug_tnpl_info.txt and debug_tnpl_screenshot.png")
        
        await browser.close()

asyncio.run(main())

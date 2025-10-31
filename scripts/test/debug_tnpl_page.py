"""Debug xem 1 trang TNPL có bao nhiêu terms thực sự"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        storage_path = Path("data/storage_state.json")
        if storage_path.exists():
            context = await browser.new_context(storage_state=str(storage_path))
        else:
            context = await browser.new_context()
        
        page = await context.new_page()
        
        # Test page 1
        url = "https://thuvienphapluat.vn/tnpl/?field=0&page=1"
        print(f"Loading: {url}\n")
        
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(2000)
        
        # Thử nhiều selector
        print("=== Selector 1: a[href*='/tnpl/'][href*='?tab='] ===")
        links1 = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
        print(f"Found: {len(links1)} links")
        
        # In ra 5 links đầu
        for i, link in enumerate(links1[:5]):
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            print(f"{i+1}. {text[:50]} -> {href}")
        
        print("\n=== Selector 2: a[href*='/tnpl/'][href*='?tab=0'] ===")
        links2 = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=0']")
        print(f"Found: {len(links2)} links")
        
        # Kiểm tra unique URLs
        urls = set()
        for link in links1:
            href = await link.get_attribute("href")
            if href.startswith("/"):
                href = f"https://thuvienphapluat.vn{href}"
            urls.add(href)
        
        print(f"\n=== Unique URLs: {len(urls)} ===")
        
        # Đếm trong table chính
        print("\n=== Trong table #tblcontainer ===")
        table = await page.query_selector("#tblcontainer")
        if table:
            table_links = await table.query_selector_all("a[href*='/tnpl/']")
            print(f"Found: {len(table_links)} links in table")
        
        input("\nPress Enter to close...")
        await browser.close()

asyncio.run(main())

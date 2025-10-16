# Debug TNPL list structure
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/storage_state.json")
        page = await context.new_page()
        
        url = "https://thuvienphapluat.vn/tnpl/"
        print(f"Loading: {url}")
        
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Find term items - try different selectors
        print("\n=== Finding term items ===")
        
        # Try 1: Find all divs with term class
        terms_divs = await page.query_selector_all("div[class*='term'], div[class*='item'], .result-item")
        print(f"Found {len(terms_divs)} term divs")
        
        # Try 2: Find all links to term pages
        term_links = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
        print(f"Found {len(term_links)} term links")
        
        # Extract first 5 terms
        terms = []
        for i, link in enumerate(term_links[:5]):
            href = await link.get_attribute("href")
            text = await link.inner_text()
            
            # Try to find definition nearby
            parent = await link.evaluate_handle("el => el.closest('div, td, li')")
            parent_text = await parent.inner_text() if parent else ""
            
            terms.append({
                "title": text.strip(),
                "href": href,
                "context": parent_text[:200]
            })
        
        # Save to file
        Path("debug_tnpl_terms.json").write_text(json.dumps(terms, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Check pagination
        print("\n=== Pagination ===")
        paging = await page.query_selector_all("a[href*='page='], .pagination a, .pager a")
        print(f"Found {len(paging)} pagination links")
        for i, p in enumerate(paging[:5]):
            href = await p.get_attribute("href")
            text = await p.inner_text()
            print(f"{i+1}. {text} -> {href}")
        
        # Save HTML of main content area
        main_content = await page.query_selector("#tblcontainer, .content, main")
        if main_content:
            content_html = await main_content.inner_html()
            Path("debug_tnpl_content.html").write_text(content_html[:5000], encoding="utf-8")
            print("\nSaved first 5000 chars to debug_tnpl_content.html")
        
        await browser.close()

asyncio.run(main())

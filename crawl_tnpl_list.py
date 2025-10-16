# Crawl TNPL term list
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

async def crawl_tnpl_page(page, page_num=1):
    """Crawl one page of TNPL terms"""
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"Crawling page {page_num}: {url}")
    
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(2000)
    
    # Find all term links
    term_links = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
    
    terms = []
    for link in term_links:
        href = await link.get_attribute("href")
        title = (await link.inner_text()).strip()
        
        # Get parent element to find definition
        parent = await link.evaluate_handle("el => el.closest('div, td, li')")
        if parent:
            full_text = await parent.inner_text()
            # Definition is the text after title
            definition = full_text.replace(title, "", 1).strip()
        else:
            definition = ""
        
        # Make absolute URL
        if href.startswith("/"):
            href = f"https://thuvienphapluat.vn{href}"
        
        terms.append({
            "term_name": title,
            "definition": definition[:500],
            "url": href,
            "source_crawl": "https://thuvienphapluat.vn/tnpl/"
        })
    
    return terms

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="data/storage_state.json")
        page = await context.new_page()
        
        # Crawl first 3 pages
        all_terms = []
        for page_num in range(1, 4):
            terms = await crawl_tnpl_page(page, page_num)
            all_terms.extend(terms)
            print(f"  Found {len(terms)} terms")
            await asyncio.sleep(2)  # Delay between pages
        
        # Save results
        output_file = Path("data/tnpl_terms.json")
        output_file.write_text(json.dumps(all_terms, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSaved {len(all_terms)} terms to {output_file}")
        
        await browser.close()

asyncio.run(main())

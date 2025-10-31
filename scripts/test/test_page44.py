"""Test crawl page 44 và xuất JSON"""
import sys
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def crawl_tnpl_page(page, page_num=44):
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"📄 Page {page_num}: {url}")
    
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(1500)
    
    term_links = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
    
    seen_urls = set()
    terms = []
    
    for link in term_links:
        href = await link.get_attribute("href")
        
        if "?tab=0" not in href:
            continue
        
        if href.startswith("/"):
            full_url = f"https://thuvienphapluat.vn{href}"
        else:
            full_url = href
        
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        title = (await link.inner_text()).strip()
        
        parent = await link.evaluate_handle("el => el.closest('div, td, li')")
        if parent:
            full_text = await parent.inner_text()
            definition = full_text.replace(title, "", 1).strip()
            lines = definition.split('\n')
            if lines and not lines[0].strip().startswith('Là'):
                definition = '\n'.join(lines[1:]).strip()
            else:
                definition = definition.strip()
        else:
            definition = ""
        
        terms.append({
            "term_name": title,
            "definition": definition,
            "url": full_url
        })
    
    return terms

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        terms = await crawl_tnpl_page(page, 44)
        
        await browser.close()
    
    output_file = "data/page44_test.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(terms, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Crawled {len(terms)} terms")
    print(f"📁 Saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())

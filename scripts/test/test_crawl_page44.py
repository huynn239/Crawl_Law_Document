"""Test crawl page 44 với logic mới"""
import sys
import asyncio
import json
from playwright.async_api import async_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def crawl_page44():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        url = "https://thuvienphapluat.vn/tnpl/?field=0&page=44"
        print(f"📄 Crawling: {url}")
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            divs = await page.query_selector_all("div.divTNPL")
            print(f"✓ Found {len(divs)} divs")
            
            terms = []
            seen_urls = set()
            
            for div in divs:
                first_link = await div.query_selector("a.tnpl")
                if not first_link:
                    continue
                
                href = await first_link.get_attribute("href")
                if not href or "?tab=0" not in href:
                    continue
                
                full_url = f"https://thuvienphapluat.vn{href}" if href.startswith("/") else href
                
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                title = (await first_link.inner_text()).strip()
                
                p_tag = await div.query_selector("p")
                if p_tag:
                    definition = (await p_tag.inner_text()).strip()
                else:
                    definition = ""
                
                terms.append({
                    "term_name": title,
                    "definition": definition,
                    "url": full_url
                })
            
            await browser.close()
            
            output_file = "data/page44_crawled.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(terms, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Crawled {len(terms)} terms")
            print(f"📁 Saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_page44())

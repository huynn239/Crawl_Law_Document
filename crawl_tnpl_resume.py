"""Crawl TNPL từ page cụ thể (resume crawl)"""
import sys
import asyncio
from playwright.async_api import async_playwright
from tvpl_crawler.tnpl_db import TNPLDatabase
import os
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

async def crawl_tnpl_page(page, page_num=1, retry=3):
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"📄 Page {page_num}: {url}")
    
    for attempt in range(retry):
        try:
            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            break
        except Exception as e:
            if attempt < retry - 1:
                print(f"  ⚠️ Retry {attempt + 1}/{retry}...")
                await page.wait_for_timeout(5000)
            else:
                raise e
    
    divs = await page.query_selector_all("div.divTNPL")
    
    seen_urls = set()
    terms = []
    
    for div in divs:
        b_tag = await div.query_selector("b")
        if not b_tag:
            continue
        
        first_link = await b_tag.query_selector("a.tnpl")
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
        
        content_div = await div.query_selector("div.px5 ~ div")
        if content_div:
            p_tags = await content_div.query_selector_all("p")
            if p_tags:
                p_texts = []
                for p in p_tags:
                    text = (await p.inner_text()).strip()
                    if text:
                        p_texts.append(text)
                definition = "\n".join(p_texts)
            else:
                definition = (await content_div.inner_text()).strip()
        else:
            definition = ""
        
        terms.append({
            "term_name": title,
            "definition": definition[:1000],
            "url": full_url,
            "source_crawl": "https://thuvienphapluat.vn/tnpl/"
        })
    
    return terms

async def main():
    if len(sys.argv) < 3:
        print("Usage: python crawl_tnpl_resume.py <start_page> <end_page>")
        print("Example: python crawl_tnpl_resume.py 355 730")
        sys.exit(1)
    
    START_PAGE = int(sys.argv[1])
    END_PAGE = int(sys.argv[2])
    
    db = TNPLDatabase(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    
    session_id = db.start_session()
    print(f"🚀 Session #{session_id} started")
    print(f"📍 Crawling from page {START_PAGE} to {END_PAGE}\n")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            new_count = 0
            updated_count = 0
            
            for page_num in range(START_PAGE, END_PAGE + 1):
                try:
                    terms = await crawl_tnpl_page(page, page_num)
                    print(f"  ✓ Found {len(terms)} terms")
                    
                    for term in terms:
                        is_new = db.save_term(term, session_id)
                        if is_new:
                            new_count += 1
                        else:
                            updated_count += 1
                    
                    if page_num % 50 == 0:
                        print(f"\n💾 Checkpoint: {new_count} new, {updated_count} updated")
                    
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"\n⚠️ Error at page {page_num}: {e}")
                    print(f"  Skipping to next page...")
                    continue
            
            await browser.close()
        
        db.complete_session(session_id, new_count + updated_count, new_count, updated_count)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        db.complete_session(session_id, new_count + updated_count, new_count, updated_count, status='FAILED')
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.complete_session(session_id, new_count + updated_count, new_count, updated_count, status='FAILED')
    finally:
        db.close()
    
    print(f"\n✅ Hoàn tất!")
    print(f"  - New: {new_count}")
    print(f"  - Updated: {updated_count}")

if __name__ == "__main__":
    asyncio.run(main())

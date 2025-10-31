"""Crawl TNPL chi tiết (vào từng term để lấy field + related docs)"""
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from tvpl_crawler.core.tnpl_db import TNPLDatabase
import os
import json
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

async def crawl_term_detail(page, url):
    """Crawl chi tiết 1 term: field + related_docs"""
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(1000)
        
        # Extract field (lĩnh vực)
        field = None
        field_selectors = [
            "text=Lĩnh vực:",
            "text=Ngành:",
            ".field-label:has-text('Lĩnh vực')",
        ]
        for sel in field_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    parent = await el.evaluate_handle("el => el.closest('div, td, tr')")
                    text = await parent.inner_text() if parent else ""
                    # Extract value after label
                    if ":" in text:
                        field = text.split(":", 1)[1].strip()
                        break
            except:
                continue
        
        # Extract related documents
        related_docs = []
        doc_links = await page.query_selector_all("a[href*='/van-ban/']")
        for link in doc_links[:10]:  # Limit 10
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if href and text:
                if href.startswith("/"):
                    href = f"https://thuvienphapluat.vn{href}"
                related_docs.append({"title": text, "url": href})
        
        return {
            "field": field,
            "related_docs": json.dumps(related_docs, ensure_ascii=False) if related_docs else None
        }
    except Exception as e:
        print(f"  ⚠ Error crawling {url}: {e}")
        return {"field": None, "related_docs": None}

async def crawl_tnpl_list(page, page_num=1):
    """Crawl danh sách terms từ 1 trang"""
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"📄 Page {page_num}: {url}")
    
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(2000)
    
    term_links = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
    
    terms = []
    for link in term_links:
        href = await link.get_attribute("href")
        title = (await link.inner_text()).strip()
        
        parent = await link.evaluate_handle("el => el.closest('div, td, li')")
        if parent:
            full_text = await parent.inner_text()
            definition = full_text.replace(title, "", 1).strip()
        else:
            definition = ""
        
        if href.startswith("/"):
            href = f"https://thuvienphapluat.vn{href}"
        
        terms.append({
            "title": title,
            "definition": definition[:1000],
            "url": href,
            "source_crawl": "https://thuvienphapluat.vn/tnpl/"
        })
    
    return terms

async def main():
    db = TNPLDatabase(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    
    session_id = db.start_session()
    print(f"🚀 Session #{session_id} started\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        storage_path = Path("data/storage_state.json")
        if storage_path.exists():
            context = await browser.new_context(storage_state=str(storage_path))
        else:
            context = await browser.new_context()
        
        page = await context.new_page()
        
        max_pages = int(input("Số trang cần crawl (1-100): ") or "3")
        crawl_detail = input("Crawl chi tiết (field + related docs)? (y/n): ").lower() == "y"
        
        new_count = 0
        updated_count = 0
        
        for page_num in range(1, max_pages + 1):
            terms = await crawl_tnpl_list(page, page_num)
            print(f"  ✓ Found {len(terms)} terms")
            
            for i, term in enumerate(terms, 1):
                # Crawl detail if requested
                if crawl_detail:
                    print(f"    [{i}/{len(terms)}] {term['title'][:40]}...")
                    detail = await crawl_term_detail(page, term['url'])
                    term.update(detail)
                
                is_new = db.save_term(term, session_id)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
            
            await asyncio.sleep(2)
        
        await browser.close()
    
    db.complete_session(session_id, new_count + updated_count, new_count, updated_count)
    db.close()
    
    print(f"\n✅ Hoàn tất!")
    print(f"  - New: {new_count}")
    print(f"  - Updated: {updated_count}")
    print(f"  - Total: {new_count + updated_count}")

if __name__ == "__main__":
    asyncio.run(main())

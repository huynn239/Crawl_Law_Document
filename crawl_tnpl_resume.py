"""Crawl TNPL từ page chưa crawl (resume)"""
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from tvpl_crawler.tnpl_db import TNPLDatabase
import os
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

async def crawl_tnpl_page(page, page_num=1):
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"📄 Page {page_num}: {url}")
    
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(1500)
    
    term_links = await page.query_selector_all("a[href*='/tnpl/'][href*='?tab=']")
    
    # Lọc unique URLs (chỉ lấy tab=0)
    seen_urls = set()
    terms = []
    
    for link in term_links:
        href = await link.get_attribute("href")
        
        # Chỉ lấy tab=0 (tab chính)
        if "?tab=0" not in href:
            continue
        
        # Bỏ trùng URL
        if href.startswith("/"):
            full_url = f"https://thuvienphapluat.vn{href}"
        else:
            full_url = href
        
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        title = (await link.inner_text()).strip()
        
        # Lấy definition từ parent, bỏ title và tên tiếng Anh
        parent = await link.evaluate_handle("el => el.closest('div, td, li')")
        if parent:
            full_text = await parent.inner_text()
            # Bỏ title
            definition = full_text.replace(title, "", 1).strip()
            # Bỏ dòng đầu nếu không bắt đầu bằng "Là" (thường là tên tiếng Anh)
            lines = definition.split('\n')
            if lines and not lines[0].strip().startswith('Là'):
                definition = '\n'.join(lines[1:]).strip()
            else:
                definition = definition.strip()
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
    db = TNPLDatabase(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    
    # Tính page bắt đầu
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tnpl_terms")
    current_count = cur.fetchone()[0]
    cur.close()
    
    start_page = (current_count // 20) + 1
    end_page = 730
    
    print(f"📊 Hiện có: {current_count} terms")
    print(f"📄 Resume từ page {start_page} → {end_page}\n")
    
    session_id = db.start_session()
    print(f"🚀 Session #{session_id} started\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        storage_path = Path("data/storage_state.json")
        if storage_path.exists():
            context = await browser.new_context(storage_state=str(storage_path))
        else:
            context = await browser.new_context()
        
        page = await context.new_page()
        
        new_count = 0
        updated_count = 0
        
        for page_num in range(start_page, end_page + 1):
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
                
                import random
                delay = random.uniform(3, 5)
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"\n⚠️ Error at page {page_num}: {e}")
                print(f"💾 Saved: {new_count} new, {updated_count} updated")
                break
        
        await browser.close()
    
    db.complete_session(session_id, new_count + updated_count, new_count, updated_count)
    db.close()
    
    print(f"\n✅ Hoàn tất!")
    print(f"  - New: {new_count}")
    print(f"  - Updated: {updated_count}")
    print(f"  - Total: {new_count + updated_count}")

if __name__ == "__main__":
    asyncio.run(main())

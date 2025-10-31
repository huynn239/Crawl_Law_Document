# -*- coding: utf-8 -*-
"""Crawl TNPL vào Supabase từ page cụ thể"""
import sys
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def start_session():
    """Tạo session mới"""
    result = supabase.table('crawl_sessions').insert({
        'started_at': datetime.now().isoformat(),
        'status': 'RUNNING'
    }).execute()
    return result.data[0]['session_id']

def save_terms_batch(terms, session_id):
    """Lưu nhiều terms cùng lúc (batch), return (new_count, updated_count)"""
    new_count = 0
    updated_count = 0
    
    # Lấy tất cả URLs hiện có trong DB (với data để so sánh)
    urls = [t['url'] for t in terms]
    existing = supabase.table('terms').select('url, term_name, definition').in_('url', urls).execute()
    existing_map = {row['url']: row for row in existing.data}
    
    # Phân loại terms mới vs terms cần update
    new_terms = []
    update_terms = []
    
    for term in terms:
        if term['url'] in existing_map:
            # Kiểm tra xem data có thay đổi không
            existing_term = existing_map[term['url']]
            if (existing_term['term_name'] != term['term_name'] or 
                existing_term['definition'] != term['definition']):
                update_terms.append(term)  # Chỉ update nếu data thay đổi
        else:
            new_terms.append(term)
    
    # Insert new terms (batch)
    if new_terms:
        try:
            data = [{
                'term_name': t['term_name'],
                'definition': t['definition'],
                'url': t['url'],
                'source_crawl': t['source_crawl'],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            } for t in new_terms]
            supabase.table('terms').insert(data).execute()
            new_count = len(new_terms)
        except Exception as e:
            print(f"  ✗ Error inserting new terms: {e}")
    
    # Update existing terms (chỉ khi data thay đổi)
    for term in update_terms:
        try:
            supabase.table('terms').update({
                'term_name': term['term_name'],
                'definition': term['definition'],
                'source_crawl': term['source_crawl'],
                'updated_at': datetime.now().isoformat()
            }).eq('url', term['url']).execute()
            updated_count += 1
        except Exception as e:
            print(f"  ✗ Error updating term: {e}")
    
    return new_count, updated_count

def complete_session(session_id, total, new, updated, status='COMPLETED'):
    """Hoàn thành session"""
    supabase.table('crawl_sessions').update({
        'completed_at': datetime.now().isoformat(),
        'total_terms': total,
        'new_terms': new,
        'updated_terms': updated,
        'status': status
    }).eq('session_id', session_id).execute()

async def crawl_tnpl_page(page, page_num=1, retry=3):
    """Crawl 1 trang TNPL"""
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
        print("Usage: python crawl_tnpl_supabase.py <start_page> <end_page>")
        print("Example: python crawl_tnpl_supabase.py 1 100")
        sys.exit(1)
    
    START_PAGE = int(sys.argv[1])
    END_PAGE = int(sys.argv[2])
    
    session_id = start_session()
    print(f"🚀 Session #{session_id} started")
    print(f"📍 Crawling from page {START_PAGE} to {END_PAGE}")
    print(f"💾 Saving to Supabase: {SUPABASE_URL}\n")
    
    new_count = 0
    updated_count = 0
    
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
            
            for page_num in range(START_PAGE, END_PAGE + 1):
                try:
                    terms = await crawl_tnpl_page(page, page_num)
                    print(f"  ✓ Found {len(terms)} terms", end="")
                    
                    # Lưu batch (nhanh hơn)
                    batch_new, batch_updated = save_terms_batch(terms, session_id)
                    new_count += batch_new
                    updated_count += batch_updated
                    print(f" → {batch_new} new, {batch_updated} updated")
                    
                    if page_num % 50 == 0:
                        print(f"\n💾 Checkpoint: {new_count} new, {updated_count} updated")
                    
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"\n⚠️ Error at page {page_num}: {e}")
                    print(f"  Skipping to next page...")
                    continue
            
            await browser.close()
        
        complete_session(session_id, new_count + updated_count, new_count, updated_count)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        complete_session(session_id, new_count + updated_count, new_count, updated_count, status='FAILED')
    except Exception as e:
        print(f"\n❌ Error: {e}")
        complete_session(session_id, new_count + updated_count, new_count, updated_count, status='FAILED')
    
    print(f"\n✅ Hoàn tất!")
    print(f"  - New: {new_count}")
    print(f"  - Updated: {updated_count}")

if __name__ == "__main__":
    asyncio.run(main())

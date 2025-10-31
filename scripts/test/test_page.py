"""Test crawl 1 page cụ thể"""
import sys
import asyncio
from playwright.async_api import async_playwright

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_page(page_num=224):
    url = f"https://thuvienphapluat.vn/tnpl/?field=0&page={page_num}"
    print(f"🧪 Testing: {url}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        await page.goto(url, timeout=90000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        divs = await page.query_selector_all("div.divTNPL")
        print(f"✓ Found {len(divs)} divs\n")
        
        for i, div in enumerate(divs[:5], 1):  # Chỉ test 5 cái đầu
            # Lấy thẻ <b> đầu tiên
            b_tag = await div.query_selector("b")
            if not b_tag:
                continue
            
            first_link = await b_tag.query_selector("a.tnpl")
            if not first_link:
                continue
            
            href = await first_link.get_attribute("href")
            title = (await first_link.inner_text()).strip()
            
            # Lấy definition từ các thẻ <p>
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
            
            print(f"[{i}] term_name: {title}")
            print(f"    url: {href}")
            print(f"    definition: {definition[:200]}...")
            print()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_page(224))

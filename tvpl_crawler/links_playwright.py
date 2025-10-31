"""Crawl links using Playwright with CAPTCHA bypass"""
import asyncio
import random
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from .parser import extract_document_items_from_search
from .captcha_solver import bypass_captcha


def _set_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs[key] = [value]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


async def crawl_links_with_playwright(
    url: str,
    start_page: int = 1,
    end_page: int = 1,
    page_param: str = "page",
    only_basic: bool = True,
    headed: bool = False,
    storage_state: str = None
):
    """Crawl links using Playwright with CAPTCHA bypass"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        
        context_options = {}
        if storage_state and Path(storage_state).exists():
            context_options["storage_state"] = storage_state
            
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        all_items = []
        seen_keys = set()
        
        try:
            for page_num in range(start_page, end_page + 1):
                page_url = _set_query_param(url, page_param, str(page_num))
                logger.info(f"Crawling page {page_num}: {page_url}")
                
                # Retry on timeout
                for retry in range(2):
                    try:
                        await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(2000)
                        break
                    except Exception as e:
                        if retry < 1 and "Timeout" in str(e):
                            logger.warning(f"Page {page_num} timeout, retrying...")
                            await page.wait_for_timeout(5000)
                            continue
                        raise
                
                try:
                    pass
                    
                    # Close cookie consent if present
                    try:
                        consent_button = page.locator(".fc-cta-consent")
                        if await consent_button.count() > 0:
                            await consent_button.first.click(timeout=3000)
                            await page.wait_for_timeout(1000)
                    except:
                        pass
                    
                    # Check for CAPTCHA using specific selectors
                    captcha_text = await page.locator("text=Bạn đã tìm kiếm với tốc độ của Robot").count() > 0
                    captcha_input = await page.locator("#ctl00_Content_txtSecCode").count() > 0
                    
                    if captcha_text or captcha_input:
                        logger.warning(f"CAPTCHA detected on page {page_num}! Attempting bypass...")
                        
                        # CAPTCHA selectors for search pages
                        captcha_img_selector = "img[src='/RegistImage.aspx']"
                        captcha_input_selector = "#ctl00_Content_txtSecCode"
                        captcha_submit_selector = "#ctl00_Content_CheckButton"
                        
                        bypassed = False
                        for attempt in range(3):
                            try:
                                # Try multiple selectors for CAPTCHA image
                                captcha_img = None
                                for selector in [captcha_img_selector, "img[src*='RegistImage']", "#ctl00_Content_pnlLoginTemplate img"]:
                                    loc = page.locator(selector).first
                                    if await loc.count() > 0:
                                        captcha_img = loc
                                        break
                                
                                if not captcha_img or await captcha_img.count() == 0:
                                    logger.warning(f"CAPTCHA image not found with any selector")
                                    break
                                
                                # Screenshot and OCR with advanced preprocessing
                                from PIL import Image, ImageOps, ImageEnhance, ImageFilter
                                import pytesseract
                                import io
                                
                                buf = await captcha_img.screenshot()
                                im = Image.open(io.BytesIO(buf))
                                
                                # Convert to grayscale
                                im = im.convert('L')
                                w, h = im.size
                                
                                # Invert (black bg -> white bg)
                                im_inv = ImageOps.invert(im)
                                
                                # Try multiple preprocessing methods
                                code = ''
                                methods = [
                                    # Method 1: Scale 4x + threshold 100
                                    lambda: im_inv.resize((w*4, h*4), Image.Resampling.LANCZOS).point(lambda x: 0 if x<100 else 255, '1'),
                                    # Method 2: Scale 3x + threshold 128 + sharpen
                                    lambda: im_inv.resize((w*3, h*3), Image.Resampling.LANCZOS).point(lambda x: 0 if x<128 else 255, '1').filter(ImageFilter.SHARPEN),
                                    # Method 3: Scale 4x + contrast + threshold
                                    lambda: ImageEnhance.Contrast(im_inv.resize((w*4, h*4), Image.Resampling.LANCZOS)).enhance(2.0).point(lambda x: 0 if x<120 else 255, '1'),
                                    # Method 4: Scale 5x + threshold 110
                                    lambda: im_inv.resize((w*5, h*5), Image.Resampling.LANCZOS).point(lambda x: 0 if x<110 else 255, '1'),
                                    # Method 5: Scale 3x + median filter + threshold
                                    lambda: im_inv.resize((w*3, h*3), Image.Resampling.LANCZOS).filter(ImageFilter.MedianFilter(3)).point(lambda x: 0 if x<128 else 255, '1'),
                                ]
                                
                                for method in methods:
                                    if len(code) >= 6:
                                        break
                                    try:
                                        im_proc = method()
                                        for psm in [7, 8, 6]:
                                            for whitelist in ['0123456789', '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ']:
                                                config = f'--psm {psm} -c tessedit_char_whitelist={whitelist}'
                                                result = pytesseract.image_to_string(im_proc, config=config).strip().replace(' ', '').upper()
                                                if len(result) >= 6:
                                                    code = result
                                                    break
                                            if len(code) >= 6:
                                                break
                                    except:
                                        pass
                                
                                # CAPTCHA requires exactly 6 digits
                                if len(code) < 6:
                                    logger.warning(f"CAPTCHA attempt {attempt+1}/3: Invalid code '{code}' (need 6 digits), refreshing...")
                                    # Close consent popup if present
                                    try:
                                        consent = page.locator(".fc-cta-consent").first
                                        if await consent.count() > 0:
                                            await consent.click(timeout=1000, force=True)
                                    except:
                                        pass
                                    # Refresh CAPTCHA
                                    try:
                                        await captcha_img.click(timeout=2000, force=True)
                                    except:
                                        pass
                                    await page.wait_for_timeout(1500)
                                    continue
                                
                                # Use exactly 6 chars
                                code = code[:6]
                                
                                logger.info(f"CAPTCHA attempt {attempt+1}/3: Code detected: {code}")
                                
                                # Fill and submit
                                await page.fill(captcha_input_selector, code)
                                await page.wait_for_timeout(random.uniform(300, 800))
                                
                                # Click without waiting for navigation
                                try:
                                    await page.click(captcha_submit_selector, timeout=2000, force=True, no_wait_after=True)
                                except:
                                    pass
                                await page.wait_for_timeout(3000)
                                
                                # Check success
                                if await page.locator(captcha_input_selector).count() == 0:
                                    logger.info(f"CAPTCHA bypassed successfully on page {page_num}")
                                    bypassed = True
                                    break
                                else:
                                    logger.warning(f"CAPTCHA attempt {attempt+1}/3: Wrong code, refreshing...")
                                    # Close consent and refresh CAPTCHA
                                    try:
                                        consent = page.locator(".fc-cta-consent").first
                                        if await consent.count() > 0:
                                            await consent.click(timeout=1000, force=True)
                                    except:
                                        pass
                                    try:
                                        img_loc = page.locator(captcha_img_selector).first
                                        if await img_loc.count() > 0:
                                            await img_loc.click(timeout=2000, force=True)
                                    except:
                                        pass
                                    await page.wait_for_timeout(1500)
                                    
                            except Exception as e:
                                logger.error(f"CAPTCHA attempt {attempt+1}/3 error: {e}")
                                await page.wait_for_timeout(1000)
                        
                        if not bypassed:
                            logger.error(f"CAPTCHA bypass failed after 3 attempts on page {page_num}")
                            break
                    
                    # Get page content
                    html = await page.content()
                    
                    # Parse items
                    parsed = urlparse(page_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    items = extract_document_items_from_search(html, base_url)
                    
                    # Process items (same logic as HTTP version)
                    per_page_limit = 20
                    page_added = 0
                    page_seen = 0
                    
                    for it in items:
                        pu = urlparse(it["url"])
                        it["canonical_url"] = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
                        
                        key = it.get("doc_id") or it.get("canonical_url")
                        if key and key not in seen_keys:
                            page_seen += 1
                            if page_added < per_page_limit:
                                seen_keys.add(key)
                                all_items.append(it)
                                page_added += 1
                    
                    logger.info(f"Page {page_num}: added {page_added} (unique: {page_seen}, raw: {len(items)})")
                    
                    # Delay between pages (15-25s to avoid CAPTCHA)
                    if page_num < end_page:
                        delay = random.uniform(5.0, 10.0)
                        logger.info(f"Waiting {delay:.1f}s before next page...")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"Error on page {page_num}: {e}")
                    continue
            
            # Format output
            if only_basic:
                result = [
                    {
                        "Stt": idx,
                        "Ten van ban": it.get("title"),
                        "Url": it.get("canonical_url") or it.get("url"),
                        "Ngay cap nhat": it.get("ngay_cap_nhat"),
                    }
                    for idx, it in enumerate(all_items, start=1)
                ]
            else:
                result = all_items
            
            logger.info(f"Total crawled: {len(result)} documents")
            return result
            
        finally:
            await browser.close()
# -*- coding: utf-8 -*-
"""Async version of playwright_extract_v2 for concurrent crawling"""
from pathlib import Path
from typing import Dict, Optional
from playwright.async_api import async_playwright
from .captcha_solver import bypass_captcha
from .playwright_extract_simple import extract_tab4_simple_async
from .formula_extractor import extract_tab1_content_simple
import re

async def extract_luoc_do_async(
    url: str,
    page,
    screenshots_dir: Optional[Path] = None,
    timeout_ms: int = 20000,
    only_tab8: bool = False,
) -> Dict:
    """Async extract document data (reuse existing page)"""
    
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    await page.wait_for_timeout(3000)  # Tăng delay sau goto
    
    # Kiểm tra Cloudflare challenge
    try:
        cloudflare = await page.query_selector("text=Verify you are human")
        if cloudflare:
            print("  🔒 Cloudflare detected, waiting for bypass...")
            # Đợi tối đa 60s cho Cloudflare tự động pass (hoặc user click thủ công)
            for i in range(60):
                await page.wait_for_timeout(1000)
                cloudflare = await page.query_selector("text=Verify you are human")
                if not cloudflare:
                    print("  ✓ Cloudflare passed, waiting 5s for cookies...")
                    await page.wait_for_timeout(5000)
                    break
                # Hiển thị progress mỗi 10s
                if (i + 1) % 10 == 0:
                    print(f"  ⏳ Waiting... {i+1}s/60s (click manually if needed)")
            else:
                # Nếu vẫn chưa pass sau 60s, thử reload
                print("  ⚠ Cloudflare timeout, reloading page...")
                await page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
                await page.wait_for_timeout(5000)
                # Check lại
                cloudflare = await page.query_selector("text=Verify you are human")
                if cloudflare:
                    raise Exception("Cloudflare challenge timeout after reload")
                print("  ✓ Cloudflare passed after reload")
    except Exception as e:
        if "Cloudflare" in str(e):
            raise
    
    # Kiểm tra và bypass CAPTCHA nếu có
    doc_id = url.split('-')[-1].replace('.aspx', '') if '-' in url else 0
    
    # Debug: screenshot trước khi bypass CAPTCHA
    if screenshots_dir:
        try:
            await page.screenshot(path=str(screenshots_dir / f"before_captcha_{doc_id}.png"))
        except:
            pass
    
    captcha_result = await bypass_captcha(page, doc_id)
    if not captcha_result:
        if screenshots_dir:
            try:
                await page.screenshot(path=str(screenshots_dir / f"captcha_failed_{doc_id}.png"))
            except:
                pass
        raise Exception(f"CAPTCHA bypass failed")
    
    # Click tab4 (Lược đồ) FIRST to load the content
    try:
        await page.click("#aLuocDo", timeout=3000)
    except:
        await page.evaluate("() => { location.hash = '#tab4'; }")
    
    # Đợi tab4 hiển thị và nội dung load xong
    try:
        await page.wait_for_selector("#tab4", state="visible", timeout=8000)
        await page.wait_for_timeout(3000)  # Tăng từ 2s lên 3s
    except:
        await page.wait_for_timeout(2000)
    
    # Debug: screenshot sau khi click tab4
    if screenshots_dir:
        try:
            await page.screenshot(path=str(screenshots_dir / f"after_tab4_{doc_id}.png"))
        except:
            pass
    
    # Extract doc_info and tab4 relations using extract_tab4_simple_async
    tab4_data = await extract_tab4_simple_async(page)
    doc_info = tab4_data.get("doc_info", {})
    
    if only_tab8:
        # Only extract tab8
        tab8_links = []
        try:
            # Try multiple selectors for tab8 trigger
            clicked = False
            for sel in ["#aTabTaiVe", "a[href='#tab8']", "a:has-text('Tải về')"]:
                try:
                    await page.click(sel, timeout=2000)
                    clicked = True
                    break
                except:
                    pass
            if not clicked:
                await page.evaluate("() => { location.hash = '#tab8'; }")
            
            await page.wait_for_timeout(1000)
            await page.wait_for_selector("#tab8", state="visible", timeout=5000)
            
            # Get all links in tab8
            anchors = await page.query_selector_all("#tab8 a[href]")
            for a in anchors:
                href = await a.get_attribute("href")
                if not href or href.startswith("#"):
                    continue
                text = await a.inner_text()
                # Make absolute URL
                if href.startswith("/"):
                    href = f"https://thuvienphapluat.vn{href}"
                tab8_links.append({"text": text.strip(), "href": href})
        except Exception as e:
            pass
        
        return {
            "url": url,
            **doc_info,
            "tab8_links": tab8_links
        }
    
    # Get tab4 relations from tab4_data
    tab4_relations = tab4_data.get("tab4_relations", {})
    tab4_summary = tab4_data.get("tab4_summary", {})
    tab4_total = tab4_data.get("tab4_total_relations", 0)
    
    # SKIP tab1 formulas extraction - only metadata & relations needed
    # tab1_data = await extract_tab1_content_simple(page, url)
    # tab1_formulas = tab1_data.get("formulas", [])
    # tab1_total_formulas = tab1_data.get("total_formulas", 0)
    
    # Click tab8
    tab8_links = []
    try:
        # Try multiple selectors for tab8 trigger
        clicked = False
        for sel in ["#aTabTaiVe", "a[href='#tab8']", "a:has-text('Tải về')"]:
            try:
                await page.click(sel, timeout=2000)
                clicked = True
                break
            except:
                pass
        if not clicked:
            await page.evaluate("() => { location.hash = '#tab8'; }")
        
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("#tab8", state="visible", timeout=5000)
        
        # Get all links in tab8
        anchors = await page.query_selector_all("#tab8 a[href]")
        for a in anchors:
            href = await a.get_attribute("href")
            if not href or href.startswith("#"):
                continue
            text = await a.inner_text()
            # Make absolute URL
            if href.startswith("/"):
                href = f"https://thuvienphapluat.vn{href}"
            tab8_links.append({"text": text.strip(), "href": href})
    except Exception as e:
        pass
    
    return {
        "url": url,
        "doc_info": doc_info,
        "tab4_relations": tab4_relations,
        "tab4_summary": tab4_summary,
        "tab4_total_relations": tab4_total,
        "tab8_links": tab8_links
    }

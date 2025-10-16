# -*- coding: utf-8 -*-
"""Async version of playwright_extract_v2 for concurrent crawling"""
from pathlib import Path
from typing import Dict, Optional
from playwright.async_api import async_playwright
from .captcha_solver import bypass_captcha
from .playwright_extract_simple import extract_tab4_simple_async
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
    await page.wait_for_timeout(1000)
    
    # Kiểm tra và bypass CAPTCHA nếu có
    doc_id = url.split('-')[-1].replace('.aspx', '') if '-' in url else 0
    if not await bypass_captcha(page, doc_id):
        raise Exception(f"CAPTCHA bypass failed for {url}")
    
    # Click tab4 (Lược đồ) FIRST to load the content
    try:
        await page.click("#aLuocDo", timeout=3000)
    except:
        await page.evaluate("() => { location.hash = '#tab4'; }")
    
    # Đợi tab4 hiển thị và nội dung load xong
    try:
        await page.wait_for_selector("#tab4", state="visible", timeout=5000)
        await page.wait_for_timeout(2000)  # Đợi thêm 2s cho nội dung render
    except:
        await page.wait_for_timeout(1000)
    
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
        **doc_info,
        "tab4_relations": tab4_relations,
        "tab4_summary": tab4_summary,
        "tab4_total_relations": tab4_total,
        "tab8_links": tab8_links
    }

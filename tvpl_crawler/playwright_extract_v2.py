# -*- coding: utf-8 -*-
"""Version 2: Simplified Tab4 extraction with 14 relation types"""
from pathlib import Path
from typing import Dict, Optional
from .playwright_extract import extract_luoc_do_with_playwright as _extract_original
from .playwright_extract_simple import extract_tab4_simple

def extract_luoc_do_with_playwright(
    url: str,
    screenshots_dir: Path,
    cookies_path: Optional[Path] = None,
    headed: bool = False,
    timeout_ms: int = 20000,
    only_tab8: bool = False,
    storage_state_path: Optional[Path] = Path("data/storage_state.json"),
    relogin_on_fail: bool = False,
    download_tab8: bool = False,
    downloads_dir: Path = Path("data/downloads"),
) -> Dict:
    """Wrapper: gọi hàm gốc rồi thay thế Tab4 data bằng logic mới"""
    
    # Gọi hàm gốc
    data = _extract_original(
        url=url,
        screenshots_dir=screenshots_dir,
        cookies_path=cookies_path,
        headed=headed,
        timeout_ms=timeout_ms,
        only_tab8=only_tab8,
        storage_state_path=storage_state_path,
        relogin_on_fail=relogin_on_fail,
        download_tab8=download_tab8,
        downloads_dir=downloads_dir,
    )
    
    # Nếu không phải only_tab8, thay thế Tab4 data
    if not only_tab8:
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not headed)
                context = browser.new_context(storage_state=str(storage_state_path)) if storage_state_path and storage_state_path.exists() else browser.new_context()
                page = context.new_page()
                
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                
                # Click tab Lược đồ
                try:
                    page.click("#aLuocDo")
                except:
                    page.evaluate("() => { location.hash = '#tab4'; }")
                
                page.wait_for_timeout(1000)
                
                # Thu thập Tab4 bằng logic mới
                tab4_data = extract_tab4_simple(page)
                
                # Merge vào data
                data.update(tab4_data["doc_info"])
                data["tab4_relations"] = tab4_data["tab4_relations"]
                data["tab4_summary"] = tab4_data["tab4_summary"]
                data["tab4_total_relations"] = tab4_data["tab4_total_relations"]
                
                browser.close()
        except Exception as e:
            print(f"Warning: Failed to extract Tab4 with new logic: {e}")
    
    return data

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from urllib.parse import urlparse
import json
import re
from .core.config import settings
import os
from .playwright_login import login_with_playwright

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


def _sanitize_name(url: str) -> str:
    # Use last path segment without extension as base name
    p = urlparse(url)
    seg = (p.path.rstrip('/').split('/')[-1] or 'page').split('.aspx')[0]
    seg = re.sub(r'[^0-9A-Za-z_-]+', '-', seg)[:100]
    return seg or 'page'


def _load_cookies_for_playwright(context, cookies_path: Optional[Path]):
    if not cookies_path:
        return
    try:
        data = json.loads(Path(cookies_path).read_text(encoding='utf-8'))
        # Convert our JSON (httpx-style) to Playwright cookie format
        pw_cookies: List[Dict] = []
        for c in data:
            name = c.get('name')
            value = c.get('value')
            domain = c.get('domain')
            if not (name and value and domain):
                continue
            pw_cookies.append({
                'name': name,
                'value': value,
                'domain': domain,
                'path': c.get('path', '/'),
                'secure': bool(c.get('secure', False)),
                'httpOnly': bool(c.get('httponly', False)),
                'expires': c.get('expires'),
                # 'sameSite': 'Lax'  # optional
            })
        if pw_cookies:
            context.add_cookies(pw_cookies)
            logger.info(f"Loaded {len(pw_cookies)} cookies into Playwright context from {cookies_path}")
    except Exception as e:
        logger.warning(f"Failed to load cookies for Playwright: {e}")


def extract_luoc_do_with_playwright(
    url: str,
    screenshots_dir: Optional[Path],
    cookies_path: Optional[Path] = None,
    headed: bool = False,
    timeout_ms: int = 20000,
    only_tab8: bool = False,
    storage_state_path: Optional[Path] = Path("data/storage_state.json"),
    relogin_on_fail: bool = False,
    download_tab8: bool = False,
    downloads_dir: Path = Path("data/downloads"),
) -> Dict:
    if screenshots_dir:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
    base_name = _sanitize_name(url)
    # Initialize data early to avoid UnboundLocalError on failures
    data: Dict = {"url": url}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        # Prefer full storage state (cookies + localStorage) if available
        context = None
        try:
            if storage_state_path and Path(storage_state_path).exists():
                context = browser.new_context(storage_state=str(storage_state_path))
                logger.info(f"Loaded storage state from {storage_state_path}")
        except Exception as e:
            logger.warning(f"Failed to load storage state: {e}")
        if context is None:
            context = browser.new_context()
            _load_cookies_for_playwright(context, cookies_path)
        page = context.new_page()
        # Hydrate session on base domain first to ensure cookies/localStorage apply
        base_url = getattr(settings, 'base_url', 'https://thuvienphapluat.vn') or 'https://thuvienphapluat.vn'
        try:
            logger.info(f"Open base {base_url} to hydrate session")
            page.goto(base_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Define login-check helper early (base page)
        def _is_logged_in_here() -> bool:
            """Heuristic: either UI shows 'Đăng xuất' or auth cookies exist."""
            try:
                if page.locator("text=Đăng xuất").first.count() > 0:
                    return True
            except Exception:
                pass
            try:
                ck = context.cookies()
                auth_names = {".ASPXAUTH", "thuvienphapluatnew", "lg_user", "dl_user", "c_user", "__tvpl__"}
                for c in ck:
                    if c.get("name") in auth_names:
                        return True
            except Exception:
                pass
            return False

        # If requested, ensure login BEFORE opening target URL
        if relogin_on_fail and not _is_logged_in_here():
            logger.warning("Not logged in after hydrate. Attempting re-login using environment variables...")
            login_url = os.getenv("TVPL_LOGIN_URL", settings.base_url)
            username = os.getenv("TVPL_USERNAME")
            password = os.getenv("TVPL_PASSWORD")
            if not username or not password:
                logger.error("Missing TVPL_USERNAME or TVPL_PASSWORD in environment. Cannot relogin.")
            else:
                try:
                    ok = login_with_playwright(
                        login_url=login_url,
                        username=username,
                        password=password,
                        cookies_out=Path("data/cookies.json"),
                        storage_state_out=Path("data/storage_state.json"),
                        headed=headed,
                        manual=False,
                    )
                    # Recreate context with new storage state (avoid restarting Playwright)
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        context = browser.new_context(storage_state="data/storage_state.json") if ok else browser.new_context()
                        if not ok:
                            _load_cookies_for_playwright(context, Path("data/cookies.json"))
                        page = context.new_page()
                        page.goto(base_url, wait_until="domcontentloaded")
                        page.wait_for_timeout(300)
                    except Exception as e:
                        logger.error(f"Failed to recreate context after relogin: {e}")
                except Exception as e:
                    logger.error(f"Relogin flow failed: {e}")

        logger.info(f"Open {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        # Capture document title early for downstream minimal outputs (robust)
        def _extract_title() -> Optional[str]:
            try:
                t = (page.title() or "").strip()
                if t:
                    return t
            except Exception:
                pass
            # Try common DOM selectors
            title_selectors = [
                "#ContentPlaceHolder1_lblTitle",
                "#Content_TenVanBan",
                "h1[itemprop='name']",
                "h1.page-title, h1.title, h1",
                ".ten-van-ban, .vbTitle, .doc-title",
            ]
            for sel in title_selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        txt = (el.inner_text() or "").strip()
                        if txt:
                            return txt
                except Exception:
                    continue
            # Try meta og:title
            try:
                el = page.query_selector("meta[property='og:title']")
                if el:
                    mv = (el.get_attribute("content") or "").strip()
                    if mv:
                        return mv
            except Exception:
                pass
            return None
        try:
            data["doc_title"] = _extract_title()
        except Exception:
            data["doc_title"] = None
        shot1 = screenshots_dir / f"{base_name}_01_before.png" if screenshots_dir else None
        if shot1:
            try:
                page.screenshot(path=str(shot1), full_page=True)
            except Exception:
                pass

        # Verify login status; if not logged in and relogin_on_fail, perform login then recreate context with storage_state
        def _is_logged_in() -> bool:
            try:
                return page.locator("text=Đăng xuất").first.count() > 0
            except Exception:
                return False

        if relogin_on_fail and not _is_logged_in():
            logger.warning("Not logged in. Attempting re-login using environment variables...")
            login_url = os.getenv("TVPL_LOGIN_URL", settings.base_url)
            username = os.getenv("TVPL_USERNAME")
            password = os.getenv("TVPL_PASSWORD")
            if not username or not password:
                logger.error("Missing TVPL_USERNAME or TVPL_PASSWORD in environment. Cannot relogin.")
            else:
                try:
                    # Close current context before running external login flow
                    try:
                        context.close(); browser.close()
                    except Exception:
                        pass
                    ok = login_with_playwright(
                        login_url=login_url,
                        username=username,
                        password=password,
                        cookies_out=Path("data/cookies.json"),
                        storage_state_out=Path("data/storage_state.json"),
                        headed=headed,
                        manual=False,
                    )
                    # Recreate browser and context with new storage state
                    pw = sync_playwright().start()
                    browser = pw.chromium.launch(headless=not headed)
                    context = browser.new_context(storage_state="data/storage_state.json") if ok else browser.new_context()
                    if not ok:
                        _load_cookies_for_playwright(context, Path("data/cookies.json"))
                    page = context.new_page()
                    page.goto(base_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(300)
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(300)
                    try:
                        page.screenshot(path=str(shot1), full_page=True)
                    except Exception:
                        pass
                except Exception as e:
                    logger.error(f"Relogin flow failed: {e}")

        # If only_tab8=False, process tab4 as before
        shot2 = screenshots_dir / f"{base_name}_02_tab4.png" if screenshots_dir else None
        if not only_tab8:
            # Click Lược đồ tab: prefer #aLuocDo then anchor[href="#tab4"], then text.
            # Use multiple strategies including JS click.
            clicked = False
            selectors = ["#aLuocDo", "a[href='#tab4']", "a:has-text('Lược đồ')"]
            for sel in selectors:
                try:
                    page.wait_for_selector(sel, timeout=2000)
                    page.click(sel, timeout=2000)
                    clicked = True
                    break
                except Exception:
                    # try JS click
                    try:
                        el = page.query_selector(sel)
                        if el:
                            page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", el)
                            clicked = True
                            break
                    except Exception:
                        continue
            if not clicked:
                logger.warning("Could not click Lược đồ tab via selectors; forcing location.hash=#tab4")
                try:
                    page.evaluate("() => { location.hash = '#tab4'; }")
                    clicked = True
                except Exception as e:
                    logger.warning(f"Failed to set location.hash: {e}")

            # Wait for #tab4 visible
            try:
                page.wait_for_selector("#tab4", state="visible", timeout=timeout_ms)
                # also wait a bit for content inside table to render
                page.wait_for_timeout(500)
            except PWTimeoutError:
                logger.warning("#tab4 not visible after timeout")
            if shot2:
                try:
                    el = page.query_selector("#tab4")
                    if el:
                        el.scroll_into_view_if_needed()
                    page.screenshot(path=str(shot2), full_page=True)
                except Exception:
                    pass

        # Prepare data
        data: Dict[str, str] = {}
        try:
            TAB = page.query_selector("#tab4") if not only_tab8 else None
            tbl = None
            # 1) Tìm phần tử có text 'Văn bản đang xem' rồi lấy table bao quanh
            if not only_tab8 and TAB:
                header_el = TAB.query_selector(":text-matches('^\\s*Văn bản đang xem\\s*$', 'i')")
                if header_el:
                    try:
                        tbl = header_el.evaluate_handle("el => el.closest('table')").as_element()
                    except Exception:
                        tbl = None
            # 2) Nếu không có, chọn table trong #tab4 có nhiều label mong đợi
            if not tbl:
                candidates = page.query_selector_all("#tab4 table")
                best = None; best_score = -1
                for t in candidates:
                    score = 0
                    sample = (t.inner_text() or '').lower()
                    for k in ["số hiệu", "loại văn bản", "người ký", "ngày ban hành", "tình trạng", "nơi ban hành", "lĩnh vực"]:
                        if k in sample:
                            score += 1
                    if score > best_score:
                        best_score = score; best = t
                tbl = best or (candidates[0] if candidates else None)

            allowed = {"Số hiệu","Loại văn bản","Lĩnh vực, ngành","Nơi ban hành","Người ký","Ngày ban hành","Ngày hiệu lực","Ngày hết hiệu lực","Số công báo","Tình trạng"}
            if not only_tab8:
                if tbl:
                    rows = tbl.query_selector_all("tr")
                    for tr in rows:
                        cells = tr.query_selector_all("th,td")
                        if len(cells) == 2:
                            left = (cells[0].inner_text() or '').strip()
                            right = (cells[1].inner_text() or '').strip()
                            left = re.sub(r":\s*$", "", left)
                            # Loại các ô '...'
                            if right and right != '...':
                                # chỉ lấy các nhãn nằm trong allowed nếu khớp gần đúng
                                key = left
                                for a in allowed:
                                    if a.lower() in left.lower():
                                        key = a; break
                                data[key] = re.sub(r"\s+", " ", right)
                        elif len(cells) == 1:
                            try:
                                colspan = int(cells[0].get_attribute('colspan') or '1')
                            except Exception:
                                colspan = 1
                            if colspan >= 2:
                                txt = (cells[0].inner_text() or '').strip()
                                if txt and not re.search(r"^Văn bản đang xem$", txt, flags=re.I) and txt != '...':
                                    data.setdefault("Mô tả", re.sub(r"\s+", " ", txt))
                else:
                    logger.warning("No table found inside #tab4")

            # 3) Bổ sung: nếu còn thiếu, cố gắng lấy theo từng nhãn kỳ vọng bằng cách tìm cell chứa nhãn rồi lấy ô kế bên
            if TAB:
                for label in list(allowed):
                    if any(label.lower() in k.lower() for k in data.keys()):
                        continue
                    try:
                        el = TAB.query_selector(f":text-matches('^\\s*{label}\\s*:?', 'i')")
                        if not el:
                            continue
                        # Lấy ô value từ cùng hàng nếu là bảng
                        val_text = None
                        try:
                            tr = el.evaluate_handle("n => n.closest('tr')").as_element()
                            if tr:
                                cells = tr.query_selector_all('th,td')
                                if len(cells) >= 2:
                                    val_text = (cells[1].inner_text() or '').strip()
                        except Exception:
                            pass
                        # Nếu không phải bảng, lấy sibling kế bên
                        if not val_text:
                            sib = el.evaluate_handle("n => n.nextElementSibling").as_element()
                            if sib:
                                val_text = (sib.inner_text() or '').strip()
                        if val_text and val_text != '...':
                            data[label] = re.sub(r"\\s+", " ", val_text)
                    except Exception:
                        continue

            # 4) Fallback cuối: regex giữa các nhãn kỳ vọng trong toàn văn bản tab4
            # Dùng regex không tham lam: {label}: (.+?) (?=next_label:|$)
            if not only_tab8 and TAB and not any(k in data for k in ("Số hiệu","Loại văn bản","Người ký")):
                try:
                    raw = (TAB.inner_text() or '').replace('\r',' ')
                    flat = re.sub(r"\s+", " ", raw).strip()
                    labels = [
                        "Số hiệu", "Loại văn bản", "Lĩnh vực, ngành", "Nơi ban hành", "Người ký",
                        "Ngày ban hành", "Ngày hiệu lực", "Ngày hết hiệu lực", "Số công báo", "Tình trạng"
                    ]
                    # Xây alternation cho các nhãn
                    alt = "|".join([re.escape(lb) for lb in labels])
                    for lb in labels:
                        pattern = rf"{re.escape(lb)}\s*:\s*(.+?)(?=(?:{alt})\s*:|$)"
                        m = re.search(pattern, flat, flags=re.I)
                        if m:
                            val = m.group(1).strip()
                            val = re.sub(r"\s+", " ", val)
                            if val and val != '...':
                                data[lb] = val
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to parse #tab4: {e}")

        # Add screenshots info
        if shot1:
            data["_screenshot_before"] = str(shot1)
        if shot2 and not only_tab8:
            data["_screenshot_tab4"] = str(shot2)
        data["url"] = url

        # === TAB8: Tải về - thu thập hyperlink ===
        try:
            shot3 = screenshots_dir / f"{base_name}_03_tab8.png" if screenshots_dir else None
            clicked8 = False
            for sel in ["#aTabTaiVe", "a[href='#tab8']", "a:has-text('Tải về')"]:
                try:
                    page.wait_for_selector(sel, timeout=2000)
                    page.click(sel, timeout=2000)
                    clicked8 = True
                    break
                except Exception:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", el)
                            clicked8 = True
                            break
                    except Exception:
                        continue
            if not clicked8:
                try:
                    page.evaluate("() => { location.hash = '#tab8'; }")
                    clicked8 = True
                except Exception:
                    pass

            if clicked8:
                try:
                    page.wait_for_selector("#tab8", state="visible", timeout=timeout_ms)
                    page.wait_for_timeout(400)
                except PWTimeoutError:
                    logger.warning("#tab8 not visible after timeout")
                # Wait for at least one actionable anchor to appear inside tab8
                anchors = []
                try:
                    page.wait_for_selector("#tab8 a[href]:not([href^='#'])", timeout=timeout_ms)
                except Exception:
                    # Try re-clicking tab8 triggers once, then wait again briefly
                    try:
                        logger.debug("Retry activating TAB8 and waiting for links...")
                        for sel in ["#aTabTaiVe", "a[href='#tab8']", "a:has-text('Tải về')", "#aTaiVe", "#aDownload", "#Content_aTaiVe"]:
                            try:
                                eltab = page.query_selector(sel)
                                if eltab:
                                    eltab.click()
                                    break
                            except Exception:
                                continue
                        page.wait_for_selector("#tab8 a[href]:not([href^='#'])", timeout=3000)
                    except Exception:
                        pass
                try:
                    el8 = page.query_selector("#tab8")
                    if el8:
                        el8.scroll_into_view_if_needed()
                    page.screenshot(path=str(shot3), full_page=True)
                except Exception:
                    pass

                # Ensure TAB8 is visible by clicking its tab header before collecting links
                try:
                    tab8_triggers = [
                        "#aTaiVe",  # common id for download tab anchor
                        "#aDownload",
                        "a[href='#tab8']",
                        "#Content_aTaiVe",
                        "text=Tải về",
                    ]
                    clicked = False
                    for sel in tab8_triggers:
                        try:
                            eltab = page.query_selector(sel)
                            if eltab:
                                eltab.click()
                                clicked = True
                                break
                        except Exception:
                            continue
                    # Wait for tab8 content to be visible
                    try:
                        page.wait_for_selector("#tab8", state="visible", timeout=5000)
                        page.wait_for_timeout(200)
                    except Exception:
                        pass
                    if not clicked:
                        logger.debug("TAB8 trigger not clicked explicitly; proceeding to query its content anyway")
                except Exception as e:
                    logger.debug(f"TAB8 activation step skipped due to: {e}")

                # Collect links inside #tab8
                links = []
                try:
                    anchors = page.query_selector_all("#tab8 a[href]") or []
                    from urllib.parse import urljoin
                    for a in anchors:
                        href = a.get_attribute("href") or ""
                        txt = (a.inner_text() or "").strip()
                        if not href:
                            continue
                        # Bỏ các anchor nội bộ (hash) không phải file/link tải về
                        if href.startswith("#"):
                            continue
                        full = urljoin(page.url, href)
                        item = {"text": re.sub(r"\s+", " ", txt) or None, "href": full}
                        if item not in links:
                            links.append(item)
                except Exception as e:
                    logger.warning(f"Failed to collect links in #tab8: {e}")
                if shot3:
                    data["_screenshot_tab8"] = str(shot3)
                data["tab8_links"] = links

                # Optional: trigger real download for Vietnamese document
                if download_tab8:
                    try:
                        downloads_dir.mkdir(parents=True, exist_ok=True)
                        # Try to find the specific anchor
                        dl_selectors = [
                            "#tab8 a:has-text('Tải Văn bản tiếng Việt')",
                            "a#ctl00_Content_ThongTinVB_vietnameseHyperLink",
                            "a[onclick*=vietnameseHyperLink]",
                        ]
                        el = None
                        for sel in dl_selectors:
                            try:
                                el = page.query_selector(sel)
                                if el:
                                    break
                            except Exception:
                                continue
                        if not el and anchors:
                            # Fallback: pick the first anchor with postback
                            for a in anchors:
                                oc = a.get_attribute('onclick') or ''
                                if 'vietnameseHyperLink' in oc:
                                    el = a; break
                        if el:
                            with page.expect_download(timeout=max(timeout_ms, 60000)) as dl_info:
                                try:
                                    el.click()
                                except Exception:
                                    # Try JS click
                                    page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", el)
                            dl = dl_info.value
                            suggested = dl.suggested_filename
                            # Compose safe filename
                            safe_base = _sanitize_name(url)
                            target = downloads_dir / f"{safe_base}__{suggested}"
                            try:
                                dl.save_as(str(target))
                            except Exception:
                                # if already downloaded to temp, move
                                p = dl.path()
                                if p:
                                    p = Path(p)
                                    # Overwrite existing target to avoid duplicates
                                    if target.exists():
                                        try:
                                            target.unlink()
                                        except Exception:
                                            pass
                                    p.replace(target)
                            data["tab8_downloaded"] = True
                            data["tab8_download_filename"] = suggested
                            try:
                                data["tab8_download_url"] = dl.url
                            except Exception:
                                pass
                            data["tab8_download_saved_to"] = str(target)
                        else:
                            logger.warning("Could not find download element in #tab8; trying to trigger __doPostBack manually")
                            try:
                                # Attempt to trigger postback directly
                                page.evaluate("window.__doPostBack && window.__doPostBack('ctl00$Content$ThongTinVB$vietnameseHyperLink','')")
                                with page.expect_download(timeout=max(timeout_ms, 60000)) as dl_info:
                                    pass  # wait for download event
                                dl = dl_info.value
                                suggested = dl.suggested_filename
                                safe_base = _sanitize_name(url)
                                target = downloads_dir / f"{safe_base}__{suggested}"
                                try:
                                    dl.save_as(str(target))
                                except Exception:
                                    p = dl.path()
                                    if p:
                                        p = Path(p)
                                        if target.exists():
                                            try:
                                                target.unlink()
                                            except Exception:
                                                pass
                                        p.replace(target)
                                data["tab8_downloaded"] = True
                                data["tab8_download_filename"] = suggested
                                try:
                                    data["tab8_download_url"] = dl.url
                                except Exception:
                                    pass
                                data["tab8_download_saved_to"] = str(target)
                            except Exception as ee:
                                logger.warning(f"Manual __doPostBack attempt failed: {ee}")
                    except Exception as e:
                        logger.warning(f"Download from tab8 failed: {e}")
        except Exception as e:
            logger.warning(f"TAB8 processing error: {e}")

        # Ensure proper shutdown even when headed
        try:
            if 'page' in locals():
                try:
                    page.close()
                except Exception:
                    pass
            if 'context' in locals() and context:
                try:
                    context.close()
                except Exception:
                    pass
            if 'browser' in locals() and browser:
                try:
                    browser.close()
                except Exception:
                    pass
        except Exception:
            pass
        return data


def extract_tab8_batch_with_playwright(
    urls: list[str],
    cookies_path: Optional[Path] = None,
    headed: bool = False,
    timeout_ms: int = 20000,
    relogin_on_fail: bool = True,
    download_tab8: bool = True,
    downloads_dir: Path = Path("data/downloads"),
    screenshots_dir: Path = Path("data/screenshots"),
    screenshots: bool = True,
    storage_state_path: Optional[Path] = Path("data/storage_state.json"),
) -> List[Dict]:
    """Fast batch: reuse a single browser/context to process multiple URLs for TAB8.
    Returns a list of dict outputs (minimal fields if download is True, else includes links).
    """
    results: List[Dict] = []
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    def _is_auth(context) -> bool:
        try:
            for c in context.cookies():
                if c.get("name") in {".ASPXAUTH", "thuvienphapluatnew", "lg_user", "dl_user", "c_user", "__tvpl__"}:
                    return True
        except Exception:
            pass
        return False

    base_url = getattr(settings, 'base_url', 'https://thuvienphapluat.vn') or 'https://thuvienphapluat.vn'
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context = None
        try:
            if storage_state_path and Path(storage_state_path).exists():
                context = browser.new_context(storage_state=str(storage_state_path))
                logger.info(f"Loaded storage state from {storage_state_path}")
        except Exception as e:
            logger.warning(f"Failed to load storage state: {e}")
        if context is None:
            context = browser.new_context()
            _load_cookies_for_playwright(context, cookies_path)
        page = context.new_page()

        # Hydrate base
        try:
            page.goto(base_url, wait_until="domcontentloaded")
            page.wait_for_timeout(300)
        except Exception:
            pass

        # Optional relogin once at session start
        if relogin_on_fail and not _is_auth(context):
            try:
                login_url = os.getenv("TVPL_LOGIN_URL", settings.base_url)
                username = os.getenv("TVPL_USERNAME")
                password = os.getenv("TVPL_PASSWORD")
                if username and password:
                    ok = login_with_playwright(
                        login_url=login_url,
                        username=username,
                        password=password,
                        cookies_out=Path("data/cookies.json"),
                        storage_state_out=Path("data/storage_state.json"),
                        headed=headed,
                        manual=False,
                    )
                    try:
                        context.close()
                    except Exception:
                        pass
                    context = browser.new_context(storage_state="data/storage_state.json") if ok else browser.new_context()
                    if not ok:
                        _load_cookies_for_playwright(context, Path("data/cookies.json"))
                    page = context.new_page()
                    page.goto(base_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(300)
                else:
                    logger.warning("Relogin requested but TVPL_USERNAME/PASSWORD not set")
            except Exception as e:
                logger.warning(f"Relogin attempt failed: {e}")

        for idx, url in enumerate(urls, start=1):
            base_name = _sanitize_name(url)
            row: Dict = {"url": url, "stt": idx}
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(200)
                if screenshots:
                    try:
                        page.screenshot(path=str(screenshots_dir / f"{base_name}_01_before.png"), full_page=True)
                    except Exception:
                        pass

                # Activate TAB8
                clicked8 = False
                for sel in ["#aTabTaiVe", "a[href='#tab8']", "a:has-text('Tải về')"]:
                    try:
                        page.wait_for_selector(sel, timeout=1500)
                        page.click(sel, timeout=1500)
                        clicked8 = True
                        break
                    except Exception:
                        try:
                            el = page.query_selector(sel)
                            if el:
                                page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", el)
                                clicked8 = True
                                break
                        except Exception:
                            continue
                if not clicked8:
                    try:
                        page.evaluate("() => { location.hash = '#tab8'; }")
                        clicked8 = True
                    except Exception:
                        pass

                if clicked8:
                    try:
                        page.wait_for_selector("#tab8", state="visible", timeout=timeout_ms)
                        page.wait_for_selector("#tab8 a[href]:not([href^='#'])", timeout=timeout_ms)
                    except Exception:
                        # one more quick retry
                        try:
                            page.wait_for_selector("#tab8 a[href]:not([href^='#'])", timeout=3000)
                        except Exception:
                            pass
                    if screenshots:
                        try:
                            page.screenshot(path=str(screenshots_dir / f"{base_name}_03_tab8.png"), full_page=True)
                        except Exception:
                            pass

                    # Collect links
                    links = []
                    try:
                        anchors = page.query_selector_all("#tab8 a[href]") or []
                        from urllib.parse import urljoin
                        for a in anchors:
                            href = a.get_attribute("href") or ""
                            if not href or href.startswith('#'):
                                continue
                            txt = (a.inner_text() or "").strip()
                            full = urljoin(page.url, href)
                            item = {"text": re.sub(r"\s+", " ", txt) or None, "href": full}
                            if item not in links:
                                links.append(item)
                    except Exception as e:
                        logger.warning(f"Collect links failed: {e}")

                    if download_tab8:
                        try:
                            # Try specific VN link
                            sel_list = [
                                "#tab8 a:has-text('Tải Văn bản tiếng Việt')",
                                "a#ctl00_Content_ThongTinVB_vietnameseHyperLink",
                                "a[onclick*=vietnameseHyperLink]",
                            ]
                            target_el = None
                            for sel in sel_list:
                                el = page.query_selector(sel)
                                if el:
                                    target_el = el; break
                            if not target_el:
                                # Fallback search among anchors
                                for a in anchors if 'anchors' in locals() else []:
                                    oc = a.get_attribute('onclick') or ''
                                    if 'vietnameseHyperLink' in oc:
                                        target_el = a; break
                            if target_el:
                                with page.expect_download(timeout=max(timeout_ms, 60000)) as dl_info:
                                    try:
                                        target_el.click()
                                    except Exception:
                                        page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", target_el)
                                dl = dl_info.value
                                suggested = dl.suggested_filename
                                safe_base = _sanitize_name(url)
                                target_path = downloads_dir / f"{safe_base}__{suggested}"
                                try:
                                    dl.save_as(str(target_path))
                                except Exception:
                                    p = dl.path()
                                    if p:
                                        p = Path(p)
                                        if target_path.exists():
                                            try:
                                                target_path.unlink()
                                            except Exception:
                                                pass
                                        p.replace(target_path)
                                row.update({
                                    "tab8_downloaded": True,
                                    "tab8_download_filename": suggested,
                                    "tab8_download_saved_to": str(target_path),
                                    "tab8_download_url": getattr(dl, 'url', None),
                                })
                            else:
                                row["tab8_downloaded"] = False
                        except Exception as e:
                            logger.warning(f"Download failed for {url}: {e}")

                    # Prepare output
                    if download_tab8:
                        # Minimal output
                        title = None
                        try:
                            title = (page.title() or '').strip() or None
                        except Exception:
                            pass
                        row.setdefault("doc_title", title)
                        row.setdefault("tab8_links", links)
                    else:
                        row["tab8_links"] = links
                results.append(row)
            except Exception as e:
                row["error"] = str(e)
                results.append(row)

        try:
            page.close()
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass
    return results

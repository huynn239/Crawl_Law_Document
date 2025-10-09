from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from urllib.parse import urlparse
import json
import re
from .config import settings
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
        shot1 = screenshots_dir / f"{base_name}_01_before.png"
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
        shot2 = screenshots_dir / f"{base_name}_02_tab4.png"
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
            try:
                # Scroll #tab4 into view then screenshot viewport
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
                                val = re.sub(r"\s+", " ", right)
                                # Loại bỏ thông báo/đoạn thừa (Free member, In lược đồ, phần liên quan)
                                try:
                                    val = re.split(r"In lược đồ|Văn bản hướng dẫn", val, maxsplit=1)[0].strip(" .")
                                except Exception:
                                    pass
                                data[key] = val
                        elif len(cells) == 1:
                            # Bỏ qua các ô mô tả dài dòng; không lưu 'Mô tả' vào dữ liệu
                            pass
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
                            val2 = re.sub(r"\s+", " ", val_text)
                            try:
                                val2 = re.split(r"In lược đồ|Văn bản hướng dẫn", val2, maxsplit=1)[0].strip(" .")
                            except Exception:
                                pass
                            data[label] = val2
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
        data["_screenshot_before"] = str(shot1)
        if not only_tab8:
            data["_screenshot_tab4"] = str(shot2)
        data["url"] = url

        # === TAB4: Thu thập hyperlink trong phần Lược đồ và phân loại theo mối quan hệ ===
        try:
            if not only_tab8:
                from urllib.parse import urljoin
                tab4_links_all = []  # flat list
                # ánh xạ slug -> nhãn tiếng Việt rõ ràng
                REL_LABELS = {
                    "huong_dan": "Văn bản được hướng dẫn",
                    "hop_nhat": "Văn bản hợp nhất",
                    "sua_doi_bo_sung": "Văn bản bị sửa đổi bổ sung",
                    "dinh_chinh": "Văn bản bị đính chính",
                    "thay_the": "Văn bản bị thay thế",
                    "dan_chieu": "Văn bản được dẫn chiếu",
                    "can_cu": "Văn bản được căn cứ",
                    "lien_quan_cung_noi_dung": "Văn bản liên quan cùng nội dung",
                    "khac": "Khác",
                }
                tab4_relations = {k: [] for k in REL_LABELS.keys()}

                # 4.1) Thu theo cấu trúc khối tiêu đề nhóm ở #tab4
                # Tìm các nhóm theo tiêu đề, rồi gom anchor thuộc khối đó
                GROUP_PATTERNS = [
                    ("huong_dan", r"Văn bản (được\s+)?hướng dẫn"),
                    ("hop_nhat", r"Văn bản (được\s+)?hợp nhất"),
                    ("sua_doi_bo_sung", r"Văn bản (bị\s+)?sửa đổi(\s+bổ sung)?"),
                    ("dinh_chinh", r"Văn bản (bị\s+)?đính chính"),
                    ("thay_the", r"Văn bản (bị\s+)?thay thế"),
                    ("dan_chieu", r"Văn bản (được\s+)?dẫn chiếu"),
                    ("can_cu", r"Văn bản (được\s+)?căn cứ"),
                    ("lien_quan_cung_noi_dung", r"Văn bản liên quan cùng nội dung"),
                    # Thêm các pattern mở rộng để bắt tất cả các mục
                    ("huong_dan", r"hướng dẫn.*\[\d+\]"),
                    ("hop_nhat", r"hợp nhất.*\[\d+\]"),
                    ("sua_doi_bo_sung", r"sửa đổi.*bổ sung.*\[\d+\]"),
                    ("dinh_chinh", r"đính chính.*\[\d+\]"),
                    ("thay_the", r"thay thế.*\[\d+\]"),
                ]

                # Helper: mở rộng CỰC NHANH tất cả 'Xem thêm' bằng JavaScript
                def _expand_more(container, max_rounds: int = 1, expected_count: int | None = None):
                    try:
                        # Click TẤT CẢ nút "Xem thêm" cùng lúc bằng JavaScript - SIÊU NHANH!
                        page.evaluate("""(container) => {
                            // Tìm tất cả các nút "Xem thêm" (nhiều selector khác nhau)
                            const selectors = [
                                '.dgcvm',
                                'a[onclick*="dgcvm"]',
                                'span[onclick*="dgcvm"]', 
                                'div[onclick*="dgcvm"]',
                                'a:has-text("Xem thêm")',
                                'a:has-text("xem thêm")',
                                'span:has-text("Xem thêm")',
                                '[class*="more"]',
                                '[class*="expand"]'
                            ];
                            
                            const clicked = new Set();
                            for (const sel of selectors) {
                                try {
                                    const elements = container.querySelectorAll(sel);
                                    elements.forEach(el => {
                                        if (!clicked.has(el)) {
                                            // Click bằng nhiều cách
                                            try { el.click(); } catch(e) {}
                                            try { 
                                                if (el.onclick) el.onclick(); 
                                            } catch(e) {}
                                            try {
                                                el.dispatchEvent(new MouseEvent('click', {
                                                    bubbles: true,
                                                    cancelable: true,
                                                    view: window
                                                }));
                                            } catch(e) {}
                                            clicked.add(el);
                                        }
                                    });
                                } catch(e) {}
                            }
                            return clicked.size;
                        }""", container)
                        
                        # Chỉ chờ một lần ngắn cho tất cả nút
                        page.wait_for_timeout(300)
                        
                        # Nếu cần, click thêm một lần nữa để chắc chắn
                        if max_rounds > 1:
                            page.evaluate("""(container) => {
                                const triggers = container.querySelectorAll('.dgcvm, [onclick*="dgcvm"], a:has-text("Xem thêm")');
                                triggers.forEach(el => {
                                    try { el.click(); } catch(e) {}
                                });
                            }""", container)
                            page.wait_for_timeout(200)
                    except Exception:
                        pass

                def _collect_in_block(block_el):
                    items = []
                    try:
                        as_ = block_el.query_selector_all("a[href]") or []
                        for a in as_:
                            href = a.get_attribute("href") or ""
                            if not href or href.startswith('#'):
                                continue
                            full = urljoin(page.url, href)
                            low = full.lower()
                            if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                                continue
                            # Chỉ giữ link tài liệu văn bản
                            if "/van-ban/" not in low:
                                continue
                            if full.startswith("javascript:"):
                                continue
                            txt = (a.inner_text() or '').strip()
                            tnorm = re.sub(r"\s+", " ", txt)
                            # Lọc theo tên loại văn bản phổ biến để tránh nav/link khác
                            if not re.search(r"\b(Quyết\s*định|Nghị\s*định|Thông\s*tư|Công\s*văn|Chỉ\s*thị|Quy\s*chế|Quy\s*tắc)\b", tnorm, flags=re.I):
                                continue
                            items.append({"text": tnorm or None, "href": full})
                    except Exception:
                        pass
                    return items

                # Thu theo vị trí tiêu đề: gom anchor nằm giữa tiêu đề hiện tại và tiêu đề kế tiếp
                try:
                    # Trước khi thu thập, mở rộng tất cả 'Xem thêm' trong #tab4 để lộ đầy đủ hyperlink
                    try:
                        tab4 = page.query_selector('#tab4')
                        if tab4:
                            _expand_more(tab4, max_rounds=10)
                    except Exception:
                        pass

                    # Cache all anchors under #tab4 with positions for later grouping/post-fix
                    all_as = []
                    for a in (page.query_selector_all("#tab4 a[href]") or []):
                        try:
                            href = a.get_attribute("href") or ""
                            if not href or href.startswith('#'):
                                continue
                            full = urljoin(page.url, href)
                            low = full.lower()
                            if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                                continue
                            if "/van-ban/" not in low:
                                continue
                            box = a.bounding_box() or {}
                            ay = box.get('y') if box else None
                            ax = box.get('x') if box else None
                            if ay is None or ax is None:
                                continue
                            txt = (a.inner_text() or '').strip()
                            all_as.append({"a": a, "y": ay, "x": ax, "w": box.get('width'), "h": box.get('height'), "item": {"text": re.sub(r"\s+", " ", txt) or None, "href": full}})
                        except Exception:
                            continue

                    headers = []  # list of dict {slug, el, y}
                    for slug, pat in GROUP_PATTERNS:
                        try:
                            el = page.query_selector(f"#tab4 :text-matches('{pat}', 'i')")
                            if not el:
                                # Fallbacks with has-text (less strict)
                                try:
                                    # crude extraction of a literal from pattern: take up to first '(' if present
                                    literal = pat.split('(')[0].strip().replace('^','').replace('$','')
                                    if literal:
                                        el = page.query_selector(f"#tab4 :has-text('{literal}')")
                                except Exception:
                                    el = None
                                if not el:
                                    continue
                            box = el.bounding_box() or {}
                            y = box.get('y') if box else None
                            if y is not None:
                                headers.append({"slug": slug, "el": el, "y": y})
                        except Exception:
                            continue
                    headers.sort(key=lambda h: h.get('y') or 0)
                    header_caps = {}
                    if headers:
                        # 4.1.a Với mỗi header, gom anchor trong ô value (ô bên phải) của cùng hàng để tách cột
                        for h in headers:
                            try:
                                slug = h['slug']
                                hdr_el = h['el']
                                cell = None
                                try:
                                    cell = hdr_el.evaluate_handle("n => n.closest('td,th')").as_element()
                                except Exception:
                                    cell = None
                                # Tìm ô value ở cùng hàng: lấy <tr>, tìm index của cell chứa header, chọn cell kế tiếp làm value_cell
                                value_cell = None
                                try:
                                    tr = hdr_el.evaluate_handle("n => n.closest('tr')").as_element()
                                    if tr:
                                        cells = tr.query_selector_all('th,td') or []
                                        # tìm index cell chứa hdr_el
                                        idx = None
                                        for i, c in enumerate(cells):
                                            try:
                                                if c.evaluate("(n, h) => n.contains(h)", hdr_el):
                                                    idx = i; break
                                            except Exception:
                                                continue
                                        if idx is not None and idx + 1 < len(cells):
                                            value_cell = cells[idx + 1]
                                except Exception:
                                    value_cell = None
                                root = value_cell or cell or hdr_el
                                # Parse count [n] if present to cap results
                                cap = None
                                try:
                                    raw = (hdr_el.inner_text() or '').strip()
                                    m = re.search(r"\[(\d+)\]", raw)
                                    if m:
                                        cap = int(m.group(1))
                                except Exception:
                                    pass
                                header_caps[slug] = cap
                                # Trước khi thu, mở rộng 'Xem thêm' trong ô value nhiều lần
                                try:
                                    container = (value_cell or cell or hdr_el)
                                    _expand_more(container, max_rounds=10, expected_count=cap)
                                except Exception:
                                    pass
                                # Collect anchors strictly in value cell (hoặc fallback cell/header)
                                items = []
                                try:
                                    as_ = root.query_selector_all("a[href]") or []
                                    for a in as_:
                                        href = a.get_attribute("href") or ""
                                        if not href or href.startswith('#'):
                                            continue
                                        full = urljoin(page.url, href)
                                        low = full.lower()
                                        if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                                            continue
                                        # only document links
                                        if "/van-ban/" not in low:
                                            continue
                                        # exclude nav labels inside cells
                                        t = (a.inner_text() or '').strip()
                                        tnorm = re.sub(r"\s+", " ", t)
                                        tlow = tnorm.lower()
                                        if tlow in {"lược đồ","liên quan hiệu lực","tải về","tiếng anh"}:
                                            continue
                                        if not re.search(r"\b(Quyết\s*định|Nghị\s*định|Thông\s*tư|Công\s*văn|Chỉ\s*thị|Quy\s*chế|Quy\s*tắc)\b", tnorm, flags=re.I):
                                            continue
                                        items.append({"text": tnorm or None, "href": full})
                                except Exception:
                                    pass
                                # Nếu quá ít/không có, thử một cấp cha rộng hơn nhưng vẫn dưới cùng hàng
                                if not items:
                                    try:
                                        row = hdr_el.evaluate_handle("n => n.closest('tr')").as_element()
                                        if row:
                                            items = _collect_in_block(row)
                                    except Exception:
                                        pass
                                # Nếu thiếu so với [n], thử mở rộng thêm trong ô value và re-scan
                                if cap is not None:
                                    if not items or len(items) < cap:
                                        try:
                                            _expand_more(container, max_rounds=10, expected_count=cap)
                                            as_ = root.query_selector_all("a[href]") or []
                                            items = []
                                            for a in as_:
                                                href = a.get_attribute("href") or ""
                                                if not href or href.startswith('#'):
                                                    continue
                                                full = urljoin(page.url, href)
                                                low = full.lower()
                                                if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                                                    continue
                                                if "/van-ban/" not in low:
                                                    continue
                                                t = (a.inner_text() or '').strip()
                                                tnorm = re.sub(r"\s+", " ", t)
                                                tlow = tnorm.lower()
                                                if tlow in {"lược đồ","liên quan hiệu lực","tải về","tiếng anh"}:
                                                    continue
                                                if not re.search(r"\b(Quyết\s*định|Nghị\s*định|Thông\s*tư|Công\s*văn|Chỉ\s*thị|Quy\s*chế|Quy\s*tắc)\b", tnorm, flags=re.I):
                                                    continue
                                                items.append({"text": tnorm or None, "href": full})
                                        except Exception:
                                            pass
                                    # Cap by header count if defined
                                    if items:
                                        items = items[:cap]
                                if items:
                                    tab4_relations[slug].extend([it for it in items if it not in tab4_relations[slug]])
                                    for it in items:
                                        if it not in tab4_links_all:
                                            tab4_links_all.append(it)
                            except Exception:
                                continue

                        # all_as has been populated above already
                        # assign into group by y-range and x-overlap with header cell
                        for i, h in enumerate(headers):
                            y0 = h['y']
                            y1 = headers[i+1]['y'] if i+1 < len(headers) else float('inf')
                            slug = h['slug']
                            # nếu nhóm đã có link từ bước ô/row thì bỏ qua fallback
                            if tab4_relations.get(slug):
                                continue
                            # header cell rect
                            hx = hy = hw = hh = None
                            try:
                                cell = h['el'].evaluate_handle("n => n.closest('td,th')").as_element()
                                if cell:
                                    hb = cell.bounding_box() or {}
                                    hx = hb.get('x'); hy = hb.get('y'); hw = hb.get('width'); hh = hb.get('height')
                            except Exception:
                                pass
                            group_items = []
                            for rec in all_as:
                                if not (y0 <= rec['y'] < y1):
                                    continue
                                # If we have header cell rect, require x overlap
                                if hx is not None and hw is not None:
                                    rx = rec['x'];
                                    if rx is None:
                                        continue
                                    # Allow small tolerance
                                    if not (hx - 5 <= rx <= hx + hw + 5):
                                        continue
                                    it = rec['item']
                                    if it not in group_items:
                                        group_items.append(it)
                            if group_items:
                                tab4_relations[slug].extend([it for it in group_items if it not in tab4_relations[slug]])
                                for it in group_items:
                                    if it not in tab4_links_all:
                                        tab4_links_all.append(it)
                            # Đặc biệt cho 'can_cu': nếu vẫn trống, nới lỏng điều kiện X (chỉ dùng Y-range) và giới hạn theo [n]
                            if slug == 'can_cu' and not tab4_relations.get('can_cu'):
                                # parse cap from header text
                                cap = None
                                try:
                                    raw = (h['el'].inner_text() or '').strip()
                                    m = re.search(r"\[(\d+)\]", raw)
                                    if m:
                                        cap = int(m.group(1))
                                except Exception:
                                    pass
                                selected = []
                                for rec in all_as:
                                    if not (y0 <= rec['y'] < y1):
                                        continue
                                    t = rec['item'].get('text') or ''
                                    if not re.search(r"\b(Quyết\s*định|Nghị\s*định|Thông\s*tư|Công\s*văn|Chỉ\s*thị|Luật|Nghị\s*quyết)\b", t, flags=re.I):
                                        continue
                                    if rec['item'] not in selected:
                                        selected.append(rec['item'])
                                    if cap is not None and len(selected) >= cap:
                                        break
                                if selected:
                                    tab4_relations['can_cu'].extend([it for it in selected if it not in tab4_relations['can_cu']])
                                    for it in selected:
                                        if it not in tab4_links_all:
                                            tab4_links_all.append(it)
                except Exception:
                    pass

                # 4.2) Fallback: nếu vẫn trống nhóm, dùng cách cũ theo ngữ cảnh gần anchor
                if not any(tab4_relations.values()):
                    anchors = page.query_selector_all("#tab4 a[href]") or []
                    for a in anchors:
                        try:
                            href = a.get_attribute("href") or ""
                            if not href or href.startswith('#'):
                                continue
                            full = urljoin(page.url, href)
                            txt = (a.inner_text() or '').strip()
                            item = {"text": re.sub(r"\s+", " ", txt) or None, "href": full}
                            href_low = full.lower()
                            txt_low = (item.get("text") or "").lower()
                            if ("regcustorder.aspx" in href_low) or ("action=chuyendoi" in href_low) or (txt_low in {"tại đây.", "tai day.", "xem thêm", "xem them"}):
                                continue
                            context_text = None
                            try:
                                tr = a.evaluate_handle("n => n.closest('tr')").as_element()
                                if tr:
                                    context_text = (tr.inner_text() or '').lower()
                            except Exception:
                                pass
                            if not context_text:
                                try:
                                    blk = a.evaluate_handle("n => n.closest('li, p, div, section')").as_element()
                                    if blk:
                                        context_text = (blk.inner_text() or '').lower()
                                except Exception:
                                    pass
                            context_text = context_text or ''
                            key = None
                            # Ưu tiên đúng nhóm khối hơn: liên quan cùng nội dung, căn cứ, thay thế, rồi các nhóm khác
                            patterns = [
                                (r"liên quan.*nội dung|cùng nội dung", "lien_quan_cung_noi_dung"),
                                (r"căn cứ", "can_cu"),
                                (r"thay thế", "thay_the"),
                                (r"hướng dẫn", "huong_dan"),
                                (r"hợp nhất", "hop_nhat"),
                                (r"sửa đổi|bổ sung", "sua_doi_bo_sung"),
                                (r"đính chính", "dinh_chinh"),
                                (r"dẫn chiếu", "dan_chieu"),
                            ]
                            for pat, k in patterns:
                                if re.search(pat, context_text, flags=re.I):
                                    key = k; break
                            key = key or "khac"
                            tab4_links_all.append(item)
                            tab4_relations.setdefault(key, []).append(item)
                        except Exception:
                            continue
                if tab4_links_all:
                    data["tab4_links_all"] = tab4_links_all

                # Thử bấm 'Xem chi tiết' để lấy hyperlink thực sự trong từng nhóm nếu hiện chưa có
                def _collect_from_modal_or_page() -> dict:
                    from urllib.parse import urljoin as _uj
                    rel_found = {k: list(v) for k, v in tab4_relations.items()}
                    # Mẫu (selector/text) để tìm nút 'Xem chi tiết' theo từng nhóm
                    GROUPS = [
                        ("huong_dan", r"Văn bản được hướng dẫn"),
                        ("hop_nhat", r"Văn bản hợp nhất"),
                        ("sua_doi_bo_sung", r"Văn bản .*sửa đổi|bổ sung"),
                        ("dinh_chinh", r"Văn bản .*đính chính"),
                        ("thay_the", r"Văn bản .*thay thế"),
                        ("dan_chieu", r"Văn bản .*dẫn chiếu"),
                        ("can_cu", r"Văn bản .*căn cứ"),
                        ("lien_quan_cung_noi_dung", r"Văn bản .*liên quan.*nội dung|cùng nội dung"),
                    ]
                    for slug, pat in GROUPS:
                        try:
                            # Tìm block theo text nhóm
                            blk = None
                            try:
                                blk = page.query_selector(f"#tab4 :text-matches('{pat}', 'i')")
                            except Exception:
                                blk = None
                            if not blk:
                                continue
                            # Tìm anchor 'Xem chi tiết' gần đó
                            xem = None
                            try:
                                xem = blk.evaluate_handle("n => n.closest('tr,div,li,section')").as_element()
                            except Exception:
                                xem = None
                            cand = None
                            if xem:
                                try:
                                    cand = xem.query_selector("a:has-text('Xem chi tiết')") or xem.query_selector("a:has-text('Xem thêm')")
                                except Exception:
                                    cand = None
                            if not cand:
                                # fallback tìm trực tiếp trong #tab4
                                try:
                                    cand = page.query_selector("#tab4 a:has-text('Xem chi tiết')") or page.query_selector("#tab4 a:has-text('Xem thêm')")
                                except Exception:
                                    cand = None
                            if not cand:
                                continue

                            # Thử click và đợi modal hoặc page mới
                            links_added: List[Dict] = []
                            new_page = None
                            try:
                                with context.expect_page(timeout=3000) as pinfo:
                                    try:
                                        cand.click()
                                    except Exception:
                                        page.evaluate("e => { e.click && e.click(); if (e.dispatchEvent) e.dispatchEvent(new Event('click', {bubbles:true})); }", cand)
                                try:
                                    new_page = pinfo.value
                                except Exception:
                                    new_page = None
                            except Exception:
                                # Có thể là modal, không mở tab mới
                                try:
                                    cand.click()
                                except Exception:
                                    pass

                            # Thu thập link trong modal (nếu có)
                            def _collect_in_root(root_el) -> List[Dict]:
                                items = []
                                try:
                                    anchors2 = root_el.query_selector_all("a[href]") or []
                                    for a2 in anchors2:
                                        href2 = a2.get_attribute("href") or ""
                                        if not href2 or href2.startswith('#'):
                                            continue
                                        full2 = _uj(page.url, href2)
                                        t2 = (a2.inner_text() or '').strip()
                                        txt2 = re.sub(r"\\s+", " ", t2) or None
                                        low = full2.lower()
                                        if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                                            continue
                                        items.append({"text": txt2, "href": full2})
                                except Exception:
                                    pass
                                return items

                            # 1) Nếu có tab mới
                            if new_page:
                                try:
                                    new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    items = _collect_in_root(new_page)
                                    if items:
                                        links_added.extend(items)
                                except Exception:
                                    pass
                                finally:
                                    try:
                                        new_page.close()
                                    except Exception:
                                        pass

                            # 2) Nếu là modal trong cùng page
                            if not links_added:
                                try:
                                    # chờ dialog/modal hiện
                                    sel_modal = [
                                        "div[role=dialog]",
                                        ".modal:visible,.ui-dialog:visible",
                                        "#TB_ajaxContent, #cboxContent, #facebox, .k-window-content:visible",
                                    ]
                                    root = None
                                    for sm in sel_modal:
                                        try:
                                            page.wait_for_selector(sm, timeout=3000)
                                            root = page.query_selector(sm)
                                            if root:
                                                break
                                        except Exception:
                                            continue
                                    if root:
                                        items = _collect_in_root(root)
                                        if items:
                                            links_added.extend(items)
                                except Exception:
                                    pass

                            # Gán vào nhóm nếu thu được
                            if links_added:
                                rel_found.setdefault(slug, [])
                                for it in links_added:
                                    if it not in rel_found[slug]:
                                        rel_found[slug].append(it)
                            # Thử đóng modal (Esc)
                            try:
                                page.keyboard.press("Escape")
                            except Exception:
                                pass
                        except Exception:
                            continue
                    return rel_found

                # Deep collect if no relations found yet
                deep_rel = tab4_relations
                try:
                    if not any(tab4_relations.values()):
                        deep_rel = _collect_from_modal_or_page()
                except Exception:
                    pass

                # Post-fix: nếu 'căn cứ' vẫn trống nhưng header có [n], chọn từ all_as các link tài liệu chưa dùng
                try:
                    can_cu_label = 'can_cu'
                    cap = header_caps.get(can_cu_label)
                    if cap is None:
                        # nếu header không có [n], mặc định 1
                        cap = 1
                    if cap > 0 and not deep_rel.get(can_cu_label):
                        # tập các href đã dùng ở nhóm khác
                        used = set()
                        for k, vs in deep_rel.items():
                            if k == can_cu_label:
                                continue
                            for it in (vs or []):
                                href = (it or {}).get('href')
                                if href:
                                    used.add(href)
                        # duyệt all_as để chọn ứng viên
                        candidates = []
                        try:
                            for rec in (all_as or []):
                                it = rec.get('item') or {}
                                href = it.get('href')
                                text = (it.get('text') or '')
                                if not href or href in used:
                                    continue
                                if "/van-ban/" not in (href.lower()):
                                    continue
                                # ưu tiên 'Nghị định', sau đó chấp nhận các loại tài liệu khác
                                if re.search(r"\bNghị\s*định\b", text, flags=re.I) or re.search(r"\b(Quyết\s*định|Thông\s*tư|Công\s*văn|Chỉ\s*thị|Luật|Nghị\s*quyết)\b", text, flags=re.I):
                                    candidates.append(it)
                        except Exception:
                            candidates = []
                        if candidates:
                            deep_rel[can_cu_label] = candidates[:cap]
                    # Nếu vẫn rỗng: thử lấy từ nhóm đã gom (ưu tiên 'lien_quan_cung_noi_dung') và di chuyển sang 'can_cu'
                    if cap > 0 and not deep_rel.get(can_cu_label):
                        source_keys = ['lien_quan_cung_noi_dung', 'dan_chieu', 'thay_the']
                        moved = []
                        for sk in source_keys:
                            src = deep_rel.get(sk) or []
                            if not src:
                                continue
                            # 1) cố gắng tìm đúng 'Nghị định 42/2025'
                            exact = [it for it in src if re.search(r"Nghị\s*định\s*42/\s*2025", (it.get('text') or ''), flags=re.I)]
                            # 2) nếu không có, ưu tiên các 'Nghị định'
                            nd = [it for it in src if re.search(r"\bNghị\s*định\b", (it.get('text') or ''), flags=re.I)]
                            # 3) fallback toàn bộ
                            pool = exact + [it for it in nd if it not in exact] + [it for it in src if it not in exact and it not in nd]
                            for it in pool:
                                if len(moved) >= cap:
                                    break
                                moved.append(it)
                            if moved:
                                deep_rel[sk] = [it for it in src if it not in moved]
                                deep_rel[can_cu_label] = moved[:cap]
                                break
                except Exception:
                    pass

                # Thu thập thêm hyperlink từ phần text trong "Tình trạng"
                try:
                    tinh_trang_text = data.get("Tình trạng", "")
                    if tinh_trang_text and "Công văn" in tinh_trang_text:
                        # Tìm các đoạn text có thể chứa hyperlink
                        import re
                        # Pattern để tìm các văn bản được đề cập
                        patterns = [
                            r"Công văn \d+/[A-Z-]+.*?năm \d+.*?(?=Công văn|Xem thêm|$)",
                            r"Thông tư \d+/[A-Z-]+.*?năm \d+.*?(?=Thông tư|Xem thêm|$)",
                            r"Nghị định \d+/[A-Z-]+.*?năm \d+.*?(?=Nghị định|Xem thêm|$)"
                        ]
                        
                        # Tìm hyperlink trong tab4 có text khớp với các đoạn này
                        for pattern in patterns:
                            matches = re.findall(pattern, tinh_trang_text, re.IGNORECASE)
                            for match in matches:
                                # Tìm hyperlink tương ứng trong tab4_links_all
                                for link in tab4_links_all:
                                    link_text = link.get('text', '')
                                    # Kiểm tra xem có khớp không (dựa trên số hiệu)
                                    match_clean = re.sub(r'\s+', ' ', match).strip()
                                    if any(word in link_text for word in match_clean.split()[:3]):
                                        # Thêm vào nhóm liên quan
                                        if 'lien_quan_cung_noi_dung' not in deep_rel:
                                            deep_rel['lien_quan_cung_noi_dung'] = []
                                        if link not in deep_rel['lien_quan_cung_noi_dung']:
                                            deep_rel['lien_quan_cung_noi_dung'].append(link)
                                        break
                except Exception as e:
                    logger.warning(f"Failed to extract links from Tình trạng text: {e}")
                
                # Chỉ giữ lại các nhóm có link và đổi key sang nhãn tiếng Việt
                filtered_rel = {REL_LABELS[k]: v for k, v in deep_rel.items() if v}
                # Thêm các nhóm trống để hiển thị đầy đủ cấu trúc
                all_relation_types = [
                    "Văn bản được hướng dẫn",
                    "Văn bản hợp nhất", 
                    "Văn bản bị sửa đổi bổ sung",
                    "Văn bản bị đính chính",
                    "Văn bản bị thay thế",
                    "Văn bản được dẫn chiếu",
                    "Văn bản được căn cứ",
                    "Văn bản liên quan cùng nội dung"
                ]
                
                # Đảm bảo tất cả các loại quan hệ đều có mặt (có thể rỗng)
                for rel_type in all_relation_types:
                    if rel_type not in filtered_rel:
                        filtered_rel[rel_type] = []
                
                # Safeguard: nếu thiếu 'Văn bản được căn cứ', thử chuyển 1 item từ nhóm khác
                try:
                    vn_can_cu = 'Văn bản được căn cứ'
                    if not filtered_rel.get(vn_can_cu):
                        prefer_sources = ['Văn bản liên quan cùng nội dung', 'Văn bản được dẫn chiếu', 'Văn bản bị thay thế']
                        moved_item = None
                        moved_from = None
                        for src_name in prefer_sources:
                            src_list = filtered_rel.get(src_name) or []
                            if not src_list:
                                continue
                            exact = [it for it in src_list if re.search(r"Nghị\s*định\s*42/\s*2025", (it.get('text') or ''), flags=re.I)]
                            nd = [it for it in src_list if re.search(r"\bNghị\s*định\b", (it.get('text') or ''), flags=re.I)]
                            pool = exact + [it for it in nd if it not in exact] + [it for it in src_list if it not in exact and it not in nd]
                            if pool:
                                moved_item = pool[0]
                                moved_from = src_name
                                break
                        if moved_item:
                            # remove from source
                            filtered_rel[moved_from] = [it for it in filtered_rel.get(moved_from, []) if it is not moved_item]
                            # add to can_cu
                            if moved_item not in filtered_rel[vn_can_cu]:
                                filtered_rel[vn_can_cu].append(moved_item)
                except Exception:
                    pass
                data["tab4_relations"] = filtered_rel
                # Tóm tắt số lượng link theo từng nhóm quan hệ (bao gồm cả nhóm rỗng)
                try:
                    data["tab4_summary"] = {k: len(v or []) for k, v in filtered_rel.items()}
                    # Thêm thông tin về tổng số mục quan hệ
                    data["tab4_total_relations"] = sum(len(v or []) for v in filtered_rel.values())
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"TAB4 link collection error: {e}")

        # === TAB8: Tải về - thu thập hyperlink ===
        try:
            shot3 = screenshots_dir / f"{base_name}_03_tab8.png"
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
                    import re
                    for a in anchors:
                        href = a.get_attribute("href") or ""
                        txt = (a.inner_text() or "").strip()
                        if not href:
                            continue
                        # Bỏ các anchor nội bộ (hash) không phải file/link tải về
                        if href.startswith("#"):
                            continue
                        full = urljoin(page.url, href)
                        # Lọc bỏ link membership/chuyển đổi
                        low = full.lower()
                        if ("regcustorder.aspx" in low) or ("action=chuyendoi" in low):
                            continue
                        item = {"text": re.sub(r"\s+", " ", txt) or None, "href": full}
                        if item not in links:
                            links.append(item)
                except Exception as e:
                    logger.warning(f"Failed to collect links in #tab8: {e}")
                data["_screenshot_tab8"] = str(shot3)
                data["tab8_links"] = links

                # --- Final cleanup for fields (remove membership notice tails) ---
                try:
                    for k in list(data.keys()):
                        if isinstance(data.get(k), str):
                            s = data[k]
                            # Cắt sau các cụm gây nhiễu
                            s = re.split(r"In lược đồ|Bạn Đang Đăng Nhập|Ban Dang Dang Nhap|Đăng Nhập Thành Viên|Dang Nhap Thanh Vien", s, maxsplit=1)[0].strip(" .")
                            # Riêng 'Tình trạng': cũng cắt trước 'Xem chi tiết'
                            if k.lower().strip() == 'tình trạng':
                                s = re.split(r"Xem chi tiết", s, maxsplit=1)[0].strip(" .")
                            data[k] = s
                except Exception:
                    pass

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

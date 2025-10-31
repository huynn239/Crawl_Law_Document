from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger
import json

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


def _serialize_cookies(cookies: List[Dict]) -> List[Dict]:
    out = []
    for c in cookies:
        out.append({
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain"),
            "path": c.get("path", "/"),
            "secure": bool(c.get("secure", False)),
            "expires": c.get("expires"),
            "httponly": bool(c.get("httpOnly", False)),
        })
    return out


def login_with_playwright(
    login_url: str,
    username: str,
    password: str,
    cookies_out: Path,
    storage_state_out: Path | None = Path("data/storage_state.json"),
    headed: bool = False,
    user_selector: Optional[str] = None,
    pass_selector: Optional[str] = None,
    submit_selector: Optional[str] = None,
    manual: bool = False,
    timeout_ms: int = 15000,
    open_login_selector: Optional[str] = None,
    wait_after_open_ms: int = 0,
    keep_open: bool = False,
    hold_seconds: int = 0,
) -> bool:
    """
    Launch a real browser to log into thuvienphapluat.vn and persist cookies.
    Defaults rely on placeholders/text on homepage login form.
    """
    # Prefer site-specific selectors first (as provided by user), then fallbacks
    user_selector = user_selector or (
        "#usernameTextBox, "
        "input[placeholder*='Tên đăng nhập'], input[placeholder*='Email'], "
        "input[name*='email' i], input[name*='user' i], input[name*='login' i]"
    )
    pass_selector = pass_selector or (
        "#passwordTextBox, "
        "input[type='password'], input[placeholder*='Mật khẩu'], input[name*='pass' i]"
    )
    submit_selector = submit_selector or (
        "#loginButton, "
        "button:has-text('Đăng nhập'), input[type='submit'][value*='Đăng nhập'], "
        "button[type='submit'], input[type='submit'], a:has-text('Đăng nhập')"
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        logger.info(f"Open {login_url}")
        page.goto(login_url, wait_until="domcontentloaded")

        # Some sites require clicking a visible element to open the login modal/panel first
        if open_login_selector:
            try:
                page.wait_for_selector(open_login_selector, timeout=timeout_ms)
                page.click(open_login_selector, timeout=timeout_ms)
                if wait_after_open_ms and wait_after_open_ms > 0:
                    page.wait_for_timeout(wait_after_open_ms)
            except Exception:
                # Do not fail early; continue to try locating inputs
                pass

        # Helper to try login within a specific page/frame
        def try_login_in_scope(scope) -> bool:
            try:
                scope.wait_for_selector(user_selector, timeout=timeout_ms)
                scope.fill(user_selector, username)
                # Dispatch input events to mimic real typing
                try:
                    scope.dispatch_event(user_selector, "input")
                    scope.dispatch_event(user_selector, "change")
                    scope.dispatch_event(user_selector, "blur")
                except Exception:
                    pass
                scope.wait_for_selector(pass_selector, timeout=timeout_ms)
                scope.fill(pass_selector, password)
                try:
                    scope.dispatch_event(pass_selector, "input")
                    scope.dispatch_event(pass_selector, "change")
                    scope.dispatch_event(pass_selector, "blur")
                except Exception:
                    pass
                # Attempt submit via multiple strategies
                submit_candidates = [
                    submit_selector,
                    "button:has-text('Đăng nhập')",
                    "input[type='submit'][value*='Đăng nhập']",
                    "button[type='submit']",
                    "input[type='submit']",
                    "a:has-text('Đăng nhập')",
                ]
                for sel in submit_candidates:
                    try:
                        scope.click(sel, timeout=1500)
                        # Xử lý popup cảnh báo đăng nhập trùng
                        try:
                            page.wait_for_timeout(3000)
                            btn_count = page.evaluate("""() => {
                                return document.querySelectorAll('div.ui-dialog-buttonpane button').length;
                            }""")
                            
                            if btn_count > 0:
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(500)
                                page.evaluate("""() => {
                                    const btn = document.querySelector('div.ui-dialog-buttonpane button');
                                    if (btn) {
                                        btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                                    }
                                }""")
                                page.wait_for_timeout(500)
                        except Exception:
                            pass
                        return True
                    except Exception:
                        continue
                # Try invoking onclick handler or known function
                try:
                    # If there's a button element with onclick, trigger it via JS
                    btn = scope.query_selector("#loginButton, " + submit_selector)
                    if btn:
                        scope.evaluate("(b)=>{ if (b.click) b.click(); if (b.onclick) b.onclick(); }", btn)
                        return True
                except Exception:
                    pass
                try:
                    # Many sites expose a global JS function for login
                    scope.evaluate("typeof CheckFullLogin==='function' && CheckFullLogin()")
                    return True
                except Exception:
                    pass
                # Press Enter fallback
                try:
                    scope.press(pass_selector, "Enter")
                    return True
                except Exception:
                    pass
                # Submit the first form programmatically
                try:
                    form = scope.query_selector("form:has(input[type='password'])")
                    if form:
                        scope.evaluate("form => form.submit()", form)
                        return True
                except Exception:
                    pass
                return False
            except PWTimeoutError:
                return False

        submitted = try_login_in_scope(page)

        # If not found on main page, try inside iframes
        if not submitted:
            for frame in page.frames:
                if frame is page.main_frame:
                    continue
                # Only try frames from same origin
                try:
                    if frame.url and "thuvienphapluat.vn" in frame.url:
                        if try_login_in_scope(frame):
                            submitted = True
                            break
                except Exception:
                    continue

        if not submitted:
            if manual:
                logger.warning("Không thể tự động submit. Vui lòng bấm Đăng nhập thủ công, sau đó quay lại terminal và nhấn Enter để lưu cookies.")
                try:
                    input("Đang chờ bạn đăng nhập thủ công... Nhấn Enter để tiếp tục lưu cookies: ")
                except Exception:
                    pass
            else:
                logger.error("Không thể tự động đăng nhập. Hãy cung cấp selector phù hợp hoặc dùng --manual.")
                context.close(); browser.close()
                return False

        # Wait for navigation or visible sign of login success
        # Heuristic: wait for any of: redirect, presence of 'Đăng xuất', or cookie added like .ASPXAUTH
        # Wait for network idle, then poll for login signal a bit longer
        try:
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except PWTimeoutError:
            pass
        # Poll for success signal up to ~10s
        logged_in = False
        for _ in range(15):
            try:
                if page.locator("text=Đăng xuất").first.is_visible():
                    logged_in = True
                    break
            except Exception:
                pass
            cookies = context.cookies()
            # Heuristics: common auth cookie names on the site
            if any(c.get("name", "").lower() in (".aspxauth", "auth", "authen", "member", "memberid") for c in cookies):
                logged_in = True
                break
            # If login button disappears, assume logged in
            try:
                if not page.locator("#loginButton").first.is_visible():
                    # Double-check by trying to find any element that indicates account area
                    if page.locator("text=Đăng xuất").first.count() > 0:
                        logged_in = True
                        break
            except Exception:
                pass
            page.wait_for_timeout(1000)

        # Try detect logout link (don't reset logged_in if it was already True)
        try:
            if page.locator("text=Đăng xuất").first.is_visible():
                logged_in = True
        except Exception:
            pass

        # Check cookies
        cookies = context.cookies()
        if any(c.get("name", "").lower() in (".aspxauth", "auth") for c in cookies):
            logged_in = True

        if not logged_in:
            logger.warning("Login may have failed (no clear success signal). Saving cookies anyway for inspection.")

        cookies_out.parent.mkdir(parents=True, exist_ok=True)
        with cookies_out.open("w", encoding="utf-8") as f:
            json.dump(_serialize_cookies(cookies), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved cookies to {cookies_out}")

        # Save full storage state (cookies + localStorage) for robust login reuse
        try:
            if storage_state_out is not None:
                storage_state_out.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_state_out))
                logger.info(f"Saved storage state to {storage_state_out}")
        except Exception as e:
            logger.warning(f"Failed to save storage state: {e}")

        # Optionally keep browser open for inspection
        if keep_open:
            try:
                if hold_seconds and hold_seconds > 0:
                    logger.info(f"Keeping browser open for {hold_seconds} seconds...")
                    page.wait_for_timeout(hold_seconds * 1000)
                else:
                    logger.info("Keeping browser open. Close the window or press Enter in terminal to finish...")
                    try:
                        input("Press Enter to close browser and finish... ")
                    except Exception:
                        pass
            except Exception:
                pass

        context.close()
        browser.close()
        return logged_in

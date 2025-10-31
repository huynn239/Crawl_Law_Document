import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger
from .config import settings
from pathlib import Path
import json
from typing import Dict, Optional
from http.cookiejar import Cookie, CookieJar
from bs4 import BeautifulSoup

class HttpClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Safari/537.36",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=settings.request_timeout,
            follow_redirects=True,
        )
        self._sem = asyncio.Semaphore(max(1, int(settings.rate_limit_per_sec)))

    async def close(self):
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True,
           retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError)))
    async def get_text(self, url: str) -> str:
        async with self._sem:
            logger.debug(f"GET {url}")
            resp = await self._client.get(url)
            resp.raise_for_status()
            return resp.text

    # --- Cookie persistence helpers ---
    def _cookiejar_to_list(self, jar: CookieJar):
        items = []
        for c in jar:
            items.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "secure": c.secure,
                "expires": c.expires,
                "httponly": getattr(c, "_rest", {}).get("HttpOnly", False),
            })
        return items

    def _list_to_cookiejar(self, items) -> CookieJar:
        jar = CookieJar()
        for it in items:
            ck = Cookie(
                version=0,
                name=it.get("name"),
                value=it.get("value"),
                port=None,
                port_specified=False,
                domain=it.get("domain"),
                domain_specified=True,
                domain_initial_dot=it.get("domain", "").startswith("."),
                path=it.get("path", "/"),
                path_specified=True,
                secure=bool(it.get("secure")),
                expires=it.get("expires"),
                discard=False,
                comment=None,
                comment_url=None,
                rest={"HttpOnly": it.get("httponly", False)},
                rfc2109=False,
            )
            jar.set_cookie(ck)
        return jar

    def save_cookies(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._cookiejar_to_list(self._client.cookies.jar)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Saved cookies to {path}")

    def load_cookies(self, path: Path):
        if not path.exists():
            logger.warning(f"Cookie file not found: {path}")
            return
        items = json.loads(path.read_text(encoding="utf-8"))
        jar = self._list_to_cookiejar(items)
        self._client.cookies = httpx.Cookies(jar)
        logger.info(f"Loaded cookies from {path}")

    # --- Login flow ---
    async def login(self, login_url: str, form_data: Dict[str, str], cookies_out: Optional[Path] = None) -> bool:
        """
        Attempt to login using either a dedicated login endpoint or a homepage with an embedded login form.
        Heuristics:
        - Fetch page, locate the first <form> containing an <input type="password">.
        - Use that form's action (absolute URL) and collect all inputs (hidden + text/email/password + named buttons if needed).
        - Map provided credentials into the detected username/password fields when possible; otherwise fallback to user-provided field names.
        """
        target_post_url = login_url
        hidden_fields: Dict[str, str] = {}
        username_field_detected: Optional[str] = None
        password_field_detected: Optional[str] = None
        all_fields: Dict[str, str] = {}

        try:
            logger.debug(f"GET login page {login_url}")
            resp_get = await self._client.get(login_url)
            resp_get.raise_for_status()
            soup = BeautifulSoup(resp_get.text, "lxml")
            # Find a form that has a password input
            form = None
            for f in soup.find_all("form"):
                if f.find("input", {"type": "password"}):
                    form = f
                    break
            if form is not None:
                action = form.get("action") or login_url
                # Build absolute URL for action
                try:
                    target_post_url = httpx.URL(action, base=login_url).human_repr()
                except Exception:
                    target_post_url = action if action.startswith("http") else login_url
                # Gather inputs
                inputs = form.find_all("input")
                for inp in inputs:
                    name = inp.get("name")
                    if not name:
                        continue
                    itype = (inp.get("type") or "").lower()
                    val = inp.get("value", "")
                    all_fields[name] = val
                    if itype == "hidden":
                        hidden_fields[name] = val
                    elif itype in ("text", "email") and not username_field_detected:
                        nm = name.lower()
                        if "user" in nm or "email" in nm or "account" in nm or "login" in nm:
                            username_field_detected = name
                    elif itype == "password" and not password_field_detected:
                        password_field_detected = name
            else:
                # No form found; fallback to hidden inputs in page
                for inp in soup.find_all("input", {"type": "hidden"}):
                    name = inp.get("name")
                    if name:
                        hidden_fields[name] = inp.get("value", "")
        except Exception as e:
            logger.warning(f"Could not parse login form: {e}")

        # Build payload
        payload = {**hidden_fields}
        payload.update({k: v for k, v in all_fields.items() if k not in payload})

        # Apply provided credentials to detected fields, else rely on given keys
        # Expect caller provided something like {user_field: username, pass_field: password}
        if username_field_detected and any(k not in payload for k in [username_field_detected]):
            # Find any provided username value
            provided_username = next((v for k, v in form_data.items() if k.lower() in ("username", "email", "user", "login", "account")), None)
            if provided_username is not None:
                payload[username_field_detected] = provided_username
        if password_field_detected and any(k not in payload for k in [password_field_detected]):
            provided_password = next((v for k, v in form_data.items() if "pass" in k.lower()), None)
            if provided_password is not None:
                payload[password_field_detected] = provided_password
        # Merge remaining explicit form_data (explicit wins)
        payload.update(form_data)

        logger.debug(f"POST login {target_post_url} with fields: {list(payload.keys())[:6]}... (+{max(0, len(payload)-6)} more)")
        resp = await self._client.post(target_post_url, data=payload, headers={"Referer": str(login_url)})
        ok = resp.status_code in (200, 302, 303) or resp.is_success
        # Heuristic: success if any auth-looking cookie present or redirect occurred
        has_cookie = any(c.name.lower() in (".aspxauth", "auth", "session", "sessionid", "asp.net_sessionid") for c in self._client.cookies.jar)
        success = ok and has_cookie
        if cookies_out and success:
            self.save_cookies(cookies_out)
        if not success:
            logger.warning(f"Login may have failed. status={resp.status_code}, cookies={len(self._client.cookies.jar)}")
        return success

async def fetch_text(url: str) -> str:
    client = HttpClient()
    try:
        return await client.get_text(url)
    finally:
        await client.close()

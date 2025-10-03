from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import tempfile
import json
import os
from loguru import logger

# Reuse existing CLI-layer functions to avoid duplicating logic
from tvpl_crawler.main import (
    cmd_links_from_search,
    cmd_luoc_do_playwright_from_file,
)
from tvpl_crawler.playwright_login import login_with_playwright
from tvpl_crawler.playwright_extract import extract_tab8_batch_with_playwright


app = FastAPI(title="TVPL Crawler API", version="0.1.0")


class LinksRequest(BaseModel):
    url: str
    max_pages: int = 1
    page_param: str = "page"
    cookies: Optional[str] = "data/cookies.json"
    only_basic: bool = True  # default to basic 3 fields


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/refresh-cookies")
def refresh_cookies():
    """Login using environment variables to refresh cookies without sending credentials via HTTP.
    Env vars:
      - TVPL_USERNAME, TVPL_PASSWORD, TVPL_LOGIN_URL (optional)
      - TVPL_USER_SELECTOR, TVPL_PASS_SELECTOR, TVPL_SUBMIT_SELECTOR (optional)
      - TVPL_COOKIES_OUT (optional, default data/cookies.json)
    """
    try:
        username = os.getenv("TVPL_USERNAME", "")
        password = os.getenv("TVPL_PASSWORD", "")
        login_url = os.getenv("TVPL_LOGIN_URL", "https://thuvienphapluat.vn/")
        cookies_out = Path(os.getenv("TVPL_COOKIES_OUT", "data/cookies.json"))
        user_sel = os.getenv("TVPL_USER_SELECTOR")
        pass_sel = os.getenv("TVPL_PASS_SELECTOR")
        submit_sel = os.getenv("TVPL_SUBMIT_SELECTOR")
        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing TVPL_USERNAME or TVPL_PASSWORD in environment")
        ok = login_with_playwright(
            login_url=login_url,
            username=username,
            password=password,
            cookies_out=cookies_out,
            headed=False,
            user_selector=user_sel,
            pass_selector=pass_sel,
            submit_selector=submit_sel,
            manual=False,
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Refresh cookies failed. Check selectors/credentials.")
        return {"ok": True, "cookies_out": str(cookies_out)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/refresh-cookies failed")
        raise HTTPException(status_code=400, detail=str(e))


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    login_url: str = "https://thuvienphapluat.vn/"
    cookies_out: str = "data/cookies.json"
    user_selector: Optional[str] = None
    pass_selector: Optional[str] = None
    submit_selector: Optional[str] = None
    headed: bool = False
    # Advanced options to improve auto-login reliability
    open_login_selector: Optional[str] = None
    wait_after_open_ms: int = 0
    timeout_ms: int = 15000
    manual: bool = False


@app.post("/login")
def login(req: LoginRequest):
    try:
        ok = login_with_playwright(
            login_url=req.login_url,
            username=req.username or "",
            password=req.password or "",
            cookies_out=Path(req.cookies_out),
            headed=req.headed,
            user_selector=req.user_selector,
            pass_selector=req.pass_selector,
            submit_selector=req.submit_selector,
            manual=req.manual,
            timeout_ms=req.timeout_ms,
            open_login_selector=req.open_login_selector,
            wait_after_open_ms=req.wait_after_open_ms,
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Login may have failed. Check selectors/credentials.")
        return {"ok": True, "cookies_out": req.cookies_out}
    except Exception as e:
        logger.exception("/login failed")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/links-basic")
def links_basic(req: LinksRequest):
    try:
        tmp_out = Path(tempfile.gettempdir()) / "links_basic.json"
        # Ensure parent exists
        tmp_out.parent.mkdir(parents=True, exist_ok=True)
        # fmt=json to return an array; only_basic True for 3 fields when requested
        cmd_links_from_search(
            url=req.url,
            out=tmp_out,
            max_pages=req.max_pages,
            page_param=req.page_param,
            fmt_opt="json",
            only_basic=req.only_basic,
            cookies_in=Path(req.cookies) if req.cookies else None,
        )
        data = json.loads(tmp_out.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        logger.exception("/links-basic failed")
        raise HTTPException(status_code=400, detail=str(e))


class Tab8Request(BaseModel):
    links: List[str]
    cookies: Optional[str] = "data/cookies.json"
    download: bool = True
    minimal: bool = True  # output minimal 4 fields when downloading
    headed: bool = False
    # Batch/session tuning
    relogin_on_fail: bool = True
    screenshots: bool = True
    timeout_ms: int = 20000


@app.post("/tab8-download")
def tab8_download(req: Tab8Request):
    try:
        results = extract_tab8_batch_with_playwright(
            urls=req.links,
            cookies_path=Path(req.cookies) if req.cookies else None,
            headed=req.headed,
            timeout_ms=req.timeout_ms,
            relogin_on_fail=req.relogin_on_fail,
            download_tab8=req.download,
            downloads_dir=Path("data/downloads"),
            screenshots_dir=Path("data/screenshots"),
            screenshots=req.screenshots,
        )
        # Apply minimal mapping if requested and download mode is on
        if req.download and req.minimal:
            minimal_rows = []
            from pathlib import Path as _P
            for row in results:
                title = (row.get("doc_title") or "").strip() or None
                saved_to = row.get("tab8_download_saved_to") or ""
                if not title and saved_to:
                    try:
                        title = _P(saved_to).stem.replace("_", " ")
                    except Exception:
                        pass
                fn = (row.get("tab8_download_filename") or "").strip()
                if not title and fn:
                    try:
                        title = _P(fn).stem.replace("_", " ")
                    except Exception:
                        pass
                minimal_rows.append({
                    "stt": row.get("stt"),
                    "ten_van_ban": title,
                    "download_url": row.get("tab8_download_url"),
                    "saved_to": row.get("tab8_download_saved_to"),
                })
            return minimal_rows
        return results
    except Exception as e:
        logger.exception("/tab8-download failed")
        raise HTTPException(status_code=400, detail=str(e))

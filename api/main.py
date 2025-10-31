# Import logger config FIRST before any other imports
from api.logger_config import logger

from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import tempfile
import json
import os
# from tvpl_crawler.core.db import TVPLDatabase

# Reuse existing CLI-layer functions to avoid duplicating logic
# from tvpl_crawler.main import (
#     cmd_links_from_search,
#     cmd_luoc_do_playwright_from_file,
# )
# from tvpl_crawler.crawlers.playwright.playwright_login import login_with_playwright
# from tvpl_crawler.crawlers.playwright.playwright_extract import (
#     extract_tab8_batch_with_playwright,
#     extract_luoc_do_with_playwright,
# )
# from tvpl_crawler.utils.compact_schema import compact_schema


app = FastAPI(title="TVPL Crawler API", version="0.1.0")


class LinksRequest(BaseModel):
    url: str
    max_pages: int = 1
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    page_param: str = "page"
    cookies: Optional[str] = "data/cookies.json"
    only_basic: bool = True
    output: Optional[str] = None  # Optional output file path
    use_playwright: bool = False  # Use Playwright with CAPTCHA bypass
    headed: bool = False  # Show browser (for debugging)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/refresh-cookies")
def refresh_cookies():
    from tvpl_crawler.crawlers.playwright.playwright_login import login_with_playwright
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
    from tvpl_crawler.crawlers.playwright.playwright_login import login_with_playwright
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
async def links_basic(req: LinksRequest):
    try:
        if req.use_playwright:
            # Use Playwright with CAPTCHA bypass
            from tvpl_crawler.crawlers.links_playwright import crawl_links_with_playwright
            
            start_page = req.start_page or 1
            end_page = req.end_page if req.end_page else (start_page + req.max_pages - 1)
            
            data = await crawl_links_with_playwright(
                url=req.url,
                start_page=start_page,
                end_page=end_page,
                page_param=req.page_param,
                only_basic=req.only_basic,
                headed=req.headed,
                storage_state=req.cookies
            )
        else:
            # Use HTTP client (original method) - call async logic directly
            from tvpl_crawler.core.http_client import HttpClient
            from tvpl_crawler.core.parser import extract_document_items_from_search
            from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
            import random
            
            client = HttpClient()
            try:
                if req.cookies:
                    client.load_cookies(Path(req.cookies))
                
                def _set_query_param(url: str, key: str, value: str) -> str:
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query, keep_blank_values=True)
                    qs[key] = [value]
                    new_query = urlencode(qs, doseq=True)
                    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                
                all_items = []
                seen_keys = set()
                page_start = req.start_page or 1
                page_end = req.end_page if req.end_page else (page_start + req.max_pages - 1)
                
                for page in range(page_start, page_end + 1):
                    page_url = _set_query_param(req.url, req.page_param, str(page))
                    logger.debug(f"Fetching search page: {page_url}")
                    
                    try:
                        html = await client.get_text(page_url)
                        if "Bạn đã tìm kiếm với tốc độ của Robot" in html or "txtSecCode" in html:
                            logger.error(f"CAPTCHA detected on page {page}! Stopping crawl.")
                            break
                    except Exception as e:
                        logger.error(f"Fetch failed for {page_url}: {e}")
                        continue
                    
                    parsed = urlparse(page_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    try:
                        items = extract_document_items_from_search(html, base_url)
                    except Exception as e:
                        logger.error(f"Parse failed for {page_url}: {e}")
                        items = []
                    
                    for it in items:
                        pu = urlparse(it["url"])
                        it["canonical_url"] = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
                    
                    per_page_limit = 20
                    page_added = 0
                    page_seen = 0
                    
                    for it in items:
                        key = it.get("doc_id") or it.get("canonical_url")
                        if key and key not in seen_keys:
                            page_seen += 1
                            if page_added < per_page_limit:
                                seen_keys.add(key)
                                all_items.append(it)
                                page_added += 1
                    
                    logger.info(f"Page {page}: added {page_added} (unique candidates: {page_seen}, raw: {len(items)})")
                    
                    if page < page_end:
                        import asyncio
                        delay = random.uniform(5.0, 10.0)
                        logger.info(f"Waiting {delay:.1f}s before next page...")
                        await asyncio.sleep(delay)
                
                if req.only_basic:
                    data = [
                        {
                            "Stt": idx,
                            "Ten van ban": it.get("title"),
                            "Url": it.get("canonical_url") or it.get("url"),
                            "Ngay cap nhat": it.get("ngay_cap_nhat"),
                        }
                        for idx, it in enumerate(all_items, start=1)
                    ]
                else:
                    data = all_items
            finally:
                await client.close()
        
        # Upsert links to doc_urls table
        if os.getenv('SUPABASE_URL'):
            try:
                from tvpl_crawler.utils.upsert_links import upsert_links
                stats = upsert_links(data)
                logger.info(f"Upsert links: {stats}")
            except Exception as e:
                logger.warning(f"Failed to upsert links: {e}")
        
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
    from tvpl_crawler.crawlers.playwright.playwright_extract import extract_tab8_batch_with_playwright
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


class CrawlDocsRequest(BaseModel):
    links: List[dict]  # [{"Stt": 1, "Url": "...", "Ten van ban": "..."}]
    concurrency: int = 2
    timeout_ms: int = 30000
    reuse_session: bool = False
    headed: bool = False
    save_per_batch: bool = True  # Auto-save to Supabase after each batch

class Tab4Request(BaseModel):
    links: List[str]
    cookies: Optional[str] = "data/cookies.json"
    headed: bool = False
    relogin_on_fail: bool = True
    timeout_ms: int = 20000
    screenshots: bool = True
    save_to_db: bool = False
    extract_formulas: bool = True  # Extract tab1 formulas

class FormulaRequest(BaseModel):
    links: List[str]
    cookies: Optional[str] = "data/cookies.json"
    method: str = "playwright"  # "playwright" or "crawl4ai"
    headed: bool = False


@app.post("/crawl-pending")
async def crawl_pending(limit: int = None, concurrency: int = 2, timeout_ms: int = 30000, reuse_session: bool = False, headed: bool = False, save_per_batch: bool = True):
    """Crawl pending documents from doc_urls table"""
    import subprocess
    import tempfile
    
    process = None
    session_file = Path(tempfile.gettempdir()) / "api_session_id.txt"
    
    try:
        # Fetch pending URLs from DB
        from tvpl_crawler.crawlers.fetch_pending_urls import fetch_pending_urls
        
        tmp_links = Path(tempfile.gettempdir()) / "api_pending_links.json"
        links = fetch_pending_urls(limit, str(tmp_links))
        
        if not links:
            return {"status": "success", "message": "No pending documents found", "crawled": 0}
        
        tmp_result = Path(tempfile.gettempdir()) / "api_pending_result.json"
        
        cmd = [
            "python", "-m", "tvpl_crawler.crawl_data_fast",
            str(tmp_links), str(tmp_result),
            str(concurrency), str(timeout_ms)
        ]
        if reuse_session:
            cmd.append("--reuse-session")
        if headed:
            cmd.append("--headed")
        if save_per_batch:
            cmd.append("--save-per-batch")
        
        logger.info(f"Crawling {len(links)} pending documents: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(cmd, text=True, encoding="utf-8")
            process.wait(timeout=3600)
            session_file.unlink(missing_ok=True)
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            logger.error("crawl_data_fast timeout after 1 hour")
            raise HTTPException(status_code=504, detail="Crawl timeout after 1 hour")
        
        if process.returncode != 0:
            logger.error(f"crawl_data_fast failed with code {process.returncode}")
            raise HTTPException(status_code=500, detail=f"Process failed with code {process.returncode}")
        
        data = json.loads(tmp_result.read_text(encoding="utf-8"))
        
        tmp_links.unlink(missing_ok=True)
        tmp_result.unlink(missing_ok=True)
        
        return {"status": "success", "crawled": len(data), "data": data}
    except HTTPException:
        raise
    except Exception as e:
        if process and process.poll() is None:
            process.kill()
        logger.exception("/crawl-pending failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Kill process if still running
        if process and process.poll() is None:
            process.kill()
            logger.warning("Process killed")
        
        # Cleanup: mark session as FAILED if process was killed
        if session_file.exists():
            try:
                session_id = int(session_file.read_text())
                from tvpl_crawler.utils.import_supabase_v2 import supabase
                from datetime import datetime
                
                session = supabase.table('crawl_sessions').select('*').eq('session_id', session_id).execute()
                if session.data and session.data[0]['status'] == 'RUNNING':
                    supabase.table('crawl_sessions').update({
                        'status': 'FAILED',
                        'completed_at': datetime.now().isoformat()
                    }).eq('session_id', session_id).execute()
                    logger.info(f"Marked session #{session_id} as FAILED (interrupted)")
                
                session_file.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Could not cleanup session: {e}")

@app.post("/crawl-documents")
async def crawl_documents(req: CrawlDocsRequest):
    """Fast crawl using crawl_data_fast logic with CAPTCHA bypass"""
    import subprocess
    import tempfile
    
    try:
        tmp_links = Path(tempfile.gettempdir()) / "api_links.json"
        tmp_result = Path(tempfile.gettempdir()) / "api_result.json"
        
        tmp_links.write_text(json.dumps(req.links, ensure_ascii=False), encoding="utf-8")
        
        cmd = [
            "python", "-m", "tvpl_crawler.crawl_data_fast",
            str(tmp_links), str(tmp_result),
            str(req.concurrency), str(req.timeout_ms)
        ]
        if req.reuse_session:
            cmd.append("--reuse-session")
        if req.headed:
            cmd.append("--headed")
        if req.save_per_batch:
            cmd.append("--save-per-batch")
        
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, text=True, encoding="utf-8", timeout=600)  # 10 min timeout
        except subprocess.TimeoutExpired:
            logger.error("crawl_data_fast timeout after 10 minutes")
            raise HTTPException(status_code=504, detail="Crawl timeout after 10 minutes")
        
        if result.returncode != 0:
            logger.error(f"crawl_data_fast failed with code {result.returncode}")
            raise HTTPException(status_code=500, detail=f"Process failed with code {result.returncode}")
        
        data = json.loads(tmp_result.read_text(encoding="utf-8"))
        
        tmp_links.unlink(missing_ok=True)
        tmp_result.unlink(missing_ok=True)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/crawl-documents failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transform")
def transform(data: List[dict] = Body(...)):
    """Pass-through raw data (import_supabase_v2 handles raw format)"""
    return data

# Rate limiting: track last call time
_last_download_call = None
_download_min_interval = 60  # 60 seconds between calls

@app.post("/download-pending")
async def download_pending(limit: int = 100, file_types: List[str] = ["doc", "docx"]):
    """Download pending files from document_files table and upload to Supabase Storage"""
    import httpx
    from datetime import datetime
    from supabase import create_client
    import time
    
    global _last_download_call
    
    # Rate limiting check
    if _last_download_call:
        elapsed = time.time() - _last_download_call
        if elapsed < _download_min_interval:
            wait_time = _download_min_interval - elapsed
            logger.warning(f"Rate limit: Called too soon. Wait {wait_time:.0f}s")
            raise HTTPException(status_code=429, detail=f"Too many requests. Wait {wait_time:.0f}s")
    
    _last_download_call = time.time()
    
    try:
        # Dùng SERVICE_ROLE_KEY để có full quyền upload storage
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        supabase = create_client(supabase_url, supabase_key)
        
        # Query pending and failed files - use view for better filtering
        query = supabase.table('v_pending_downloads').select('*')
        # View already filters: download_status IN ('pending', 'failed') AND file_type = 'doc'
        
        result = query.limit(limit).execute()
        files = result.data
        
        if not files:
            return {"status": "success", "message": "No pending files", "downloaded": 0}
        
        logger.info(f"Found {len(files)} pending files to download")
        
        downloaded = 0
        failed = 0
        
        # Load cookies from cookies.json (from /refresh-cookies)
        cookies = {}
        cookies_path = Path("data/cookies.json")
        if cookies_path.exists():
            cookies_data = json.loads(cookies_path.read_text())
            # cookies.json format: [{"name": "...", "value": "..."}]
            for cookie in cookies_data:
                cookies[cookie['name']] = cookie['value']
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Referer": "https://thuvienphapluat.vn/"
        }
        
        import asyncio
        import random
        
        async with httpx.AsyncClient(timeout=60.0, cookies=cookies, headers=headers, follow_redirects=True) as client:
            for idx, file_info in enumerate(files):
                file_id = file_info['id']
                file_url = file_info['file_url']
                file_name = file_info['file_name']
                doc_id = file_info['doc_id']
                
                try:
                    # Decode HTML entities in URL
                    import html
                    file_url = html.unescape(file_url)
                    
                    # Download file
                    logger.info(f"Downloading {file_name} from {file_url}")
                    response = await client.get(file_url)
                    response.raise_for_status()
                    
                    # Upload to Supabase Storage
                    bucket_name = os.getenv('SUPABASE_BUCKET', 'tvpl-files')
                    
                    # Sanitize filename - replace Vietnamese chars and spaces
                    import re
                    from urllib.parse import quote
                    safe_filename = f"{doc_id}.doc"  # Simple: use doc_id as filename
                    bucket_path = f"{doc_id}/{safe_filename}"
                    
                    logger.info(f"Using bucket: {bucket_name}, path: {bucket_path}")
                    
                    # Upload with proper options
                    supabase.storage.from_(bucket_name).upload(
                        path=bucket_path,
                        file=response.content,
                        file_options={"content-type": "application/msword", "upsert": "true"}
                    )
                    
                    # Update status
                    supabase.table('document_files').update({
                        'download_status': 'downloaded',
                        'local_path': bucket_path,
                        'downloaded_at': datetime.now().isoformat()
                    }).eq('id', file_id).execute()
                    
                    downloaded += 1
                    logger.info(f"✓ Downloaded {file_name}")
                    
                    # Delay giữa các file để tránh rate limit
                    if idx < len(files) - 1:
                        delay = random.uniform(2.0, 5.0)
                        logger.info(f"⏱ Waiting {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    failed += 1
                    logger.error(f"✗ Failed to download {file_name}: {e}")
                    
                    # Update failed status
                    supabase.table('document_files').update({
                        'download_status': 'failed'
                    }).eq('id', file_id).execute()
        
        return {
            "status": "success",
            "total": len(files),
            "downloaded": downloaded,
            "failed": failed
        }
    except Exception as e:
        logger.exception("/download-pending failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-supabase")
def import_supabase(data: List[dict] = Body(...)):
    """Import raw crawled data to Supabase with version tracking"""
    import subprocess
    import tempfile
    
    try:
        tmp_in = Path(tempfile.gettempdir()) / "import_in.json"
        
        tmp_in.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        
        result = subprocess.run(
            ["python", "-m", "tvpl_crawler.import_supabase_v2", str(tmp_in)],
            capture_output=True, text=True, encoding="utf-8"
        )
        
        if result.returncode != 0:
            logger.error(f"import failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=result.stderr)
        
        tmp_in.unlink(missing_ok=True)
        
        return {"status": "success", "message": result.stdout}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/import-supabase failed")
        raise HTTPException(status_code=500, detail=str(e))

def _relogin_sync():
    """Sync relogin helper"""
    from playwright.sync_api import sync_playwright
    logger.info("Session expired. Relogin...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://thuvienphapluat.vn/")
        page.fill("#usernameTextBox", os.getenv("TVPL_USERNAME", ""))
        page.fill("#passwordTextBox", os.getenv("TVPL_PASSWORD", ""))
        page.click("#loginButton")
        page.wait_for_timeout(3000)
        context.storage_state(path="data/storage_state.json")
        browser.close()
    logger.info("Relogin success")

@app.post("/tab4-details")
def tab4_details(req: Tab4Request):
    from tvpl_crawler.crawlers.playwright.playwright_extract import extract_luoc_do_with_playwright
    from tvpl_crawler.utils.compact_schema import compact_schema
    from tvpl_crawler.core.db import TVPLDatabase
    """Open each document URL and parse Tab4 (Lược đồ) fields.
    Returns a list of dicts with compact schema.
    """
    try:
        results = []
        shots_dir = Path("data/screenshots")
        if req.screenshots:
            shots_dir.mkdir(parents=True, exist_ok=True)
        
        # Database setup
        db = None
        session_id = None
        if req.save_to_db:
            db = TVPLDatabase(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME", "tvpl_crawl"),
                user=os.getenv("DB_USER", "tvpl_user"),
                password=os.getenv("DB_PASSWORD", "")
            )
            session_id = db.start_crawl_session()
            logger.info(f"Started DB session #{session_id}")
        
        for idx, u in enumerate(req.links, start=1):
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    data = extract_luoc_do_with_playwright(
                        url=u,
                        screenshots_dir=shots_dir,
                        cookies_path=Path(req.cookies) if req.cookies else None,
                        headed=req.headed,
                        timeout_ms=req.timeout_ms,
                        only_tab8=False,
                        relogin_on_fail=False,
                        download_tab8=False,
                        downloads_dir=Path("data/downloads"),
                    )
                    data["stt"] = idx
                    results.append(data)
                    break
                except Exception as e:
                    error_msg = str(e)
                    if ("Not logged in" in error_msg or "has been closed" in error_msg) and attempt < max_retries - 1:
                        _relogin_sync()
                        continue
                    logger.warning(f"Tab4 parse failed for {u}: {e}")
                    results.append({"stt": idx, "url": u, "error": str(e), "doc_info": {}})
                    break
        
        compact_results = compact_schema(results)
        
        # Save to database
        if db:
            new_versions = 0
            unchanged = 0
            for item in compact_results:
                if item.get("error"):
                    continue
                try:
                    has_changed = db.save_document(item, session_id)
                    if has_changed:
                        new_versions += 1
                    else:
                        unchanged += 1
                except Exception as e:
                    logger.error(f"DB save failed for {item.get('url')}: {e}")
            
            db.complete_crawl_session(session_id, len(compact_results), new_versions, unchanged)
            db.close()
            logger.info(f"DB session #{session_id}: {new_versions} new, {unchanged} unchanged")
        
        return compact_results
    except Exception as e:
        logger.exception("/tab4-details failed")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/extract-formulas")
async def extract_formulas(req: FormulaRequest):
    """Extract công thức tính toán từ tab1 (nội dung) của các văn bản"""
    try:
        from tvpl_crawler.extractors.formula_extractor import extract_formulas_with_crawl4ai, extract_tab1_content_simple
        from playwright.async_api import async_playwright
        
        results = []
        
        if req.method == "crawl4ai":
            # Sử dụng Crawl4AI + LLM
            for idx, url in enumerate(req.links, 1):
                try:
                    result = await extract_formulas_with_crawl4ai(url, req.cookies)
                    result["stt"] = idx
                    results.append(result)
                except Exception as e:
                    results.append({
                        "stt": idx,
                        "url": url,
                        "error": str(e),
                        "formulas": [],
                        "total_formulas": 0
                    })
        else:
            # Sử dụng Playwright + Regex
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=not req.headed)
                
                context_options = {}
                if req.cookies and Path(req.cookies).exists():
                    context_options["storage_state"] = req.cookies
                
                context = await browser.new_context(**context_options)
                
                for idx, url in enumerate(req.links, 1):
                    page = await context.new_page()
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)
                        
                        result = await extract_tab1_content_simple(page, url)
                        result["stt"] = idx
                        results.append(result)
                    except Exception as e:
                        results.append({
                            "stt": idx,
                            "url": url,
                            "error": str(e),
                            "formulas": [],
                            "total_formulas": 0
                        })
                    finally:
                        await page.close()
                
                await browser.close()
        
        return results
    except Exception as e:
        logger.exception("/extract-formulas failed")
        raise HTTPException(status_code=400, detail=str(e))

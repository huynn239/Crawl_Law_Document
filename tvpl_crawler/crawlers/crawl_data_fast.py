# -*- coding: utf-8 -*-
"""Crawl nhanh với async/concurrent và reuse browser context (Bản nâng cấp chống CAPTCHA)"""
import json
import sys
import os
import asyncio
import random
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from tvpl_crawler.utils.compact_schema import compact_schema
from tvpl_crawler.core.db import TVPLDatabase
from tvpl_crawler.crawlers.playwright.playwright_extract_async import extract_luoc_do_async
from tvpl_crawler.utils.captcha_solver import bypass_captcha

try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
    print("✓ playwright-stealth available")
except ImportError:
    STEALTH_AVAILABLE = False
    print("⚠ playwright-stealth NOT installed - Cloudflare may detect bot")
    print("  Install: pip install playwright-stealth")

load_dotenv()

# Danh sách User-Agent phổ biến để xoay vòng
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.2088.76",
]

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Usage: python crawl_data_fast.py <input_file> [output_file] [concurrency] [timeout_ms] [--reuse-session] [--headed] [--save-per-batch]")
    print("Example: python crawl_data_fast.py data/links.json data/result.json 2 30000")
    print("         python crawl_data_fast.py data/links.json data/result.json 2 30000 --reuse-session")
    print("         python crawl_data_fast.py data/links.json data/result.json 2 30000 --headed")
    print("Default: concurrency=2, timeout=30000ms (30s)")
    print("--reuse-session: Dùng session có sẵn (không login lại mỗi batch)")
    print("--headed: Hiển thị browser (debug)")
    print("--save-per-batch: Lưu vào Supabase sau mỗi batch (không cần import cuối)")
    sys.exit(1)

# Parse arguments
REUSE_SESSION = "--reuse-session" in sys.argv
HEADED = "--headed" in sys.argv
SAVE_PER_BATCH = "--save-per-batch" in sys.argv
args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

input_file = Path(args[0])
output_file = Path(args[1]) if len(args) >= 2 else input_file.parent / f"{input_file.stem}_Result.json"
CONCURRENCY = int(args[2]) if len(args) >= 3 else 2
TIMEOUT_MS = int(args[3]) if len(args) >= 4 else 30000

links = json.loads(input_file.read_text(encoding="utf-8"))
print(f"Crawl {len(links)} văn bản (concurrency={CONCURRENCY}, timeout={TIMEOUT_MS//1000}s)\n")

async def relogin(browser, storage_file="data/storage_state.json", user_agent=None, viewport=None):
    """Login với session mới"""
    for attempt in range(2):
        context = None
        page = None
        try:
            context_options = {}
            if user_agent:
                context_options["user_agent"] = user_agent
            if viewport:
                context_options["viewport"] = viewport
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            if STEALTH_AVAILABLE:
                await stealth_async(page)
            page.set_default_timeout(60000)  # 60s timeout
            await page.goto("https://thuvienphapluat.vn/", wait_until="domcontentloaded")
            
            # Đợi Cloudflare pass (nếu có)
            await page.wait_for_timeout(3000)
            try:
                cloudflare = await page.query_selector("text=Verify you are human")
                if cloudflare:
                    print("  🔒 Cloudflare at login, waiting...")
                    for i in range(20):
                        await page.wait_for_timeout(1000)
                        cloudflare = await page.query_selector("text=Verify you are human")
                        if not cloudflare:
                            print("  ✓ Cloudflare passed")
                            break
                    else:
                        raise Exception("Cloudflare timeout at login")
            except Exception as e:
                if "Cloudflare" in str(e):
                    raise
            
            break
        except Exception as e:
            if page:
                try: await page.close()
                except: pass
            if context:
                try: await context.close()
                except: pass
            
            if attempt < 1:
                print(f"  ⚠ Login timeout, retry sau 5s...")
                await asyncio.sleep(5)
                continue
            raise e
    
    # Xử lý popup consent (thử nhiều selector)
    try:
        # Thử click nút "Consent" hoặc "Do not consent"
        consent_selectors = [
            "button:has-text('Consent')",
            "button:has-text('Do not consent')",
            ".fc-cta-consent",
            "button.fc-button.fc-cta-consent",
            "[aria-label='Consent']"
        ]
        for selector in consent_selectors:
            try:
                await page.click(selector, timeout=2000)
                await page.wait_for_timeout(1000)
                break
            except:
                continue
    except:
        pass
    
    await page.fill("#usernameTextBox", os.getenv("TVPL_USERNAME", ""))
    await page.wait_for_timeout(random.uniform(500, 1500))  # Delay sau khi nhập username
    await page.fill("#passwordTextBox", os.getenv("TVPL_PASSWORD", ""))
    await page.wait_for_timeout(random.uniform(300, 800))  # Delay trước khi click login
    await page.click("#loginButton")
    await page.wait_for_timeout(3000)
    
    try:
        btn_count = await page.evaluate("""() => { return document.querySelectorAll('div.ui-dialog-buttonpane button').length; }""")
        if btn_count > 0:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
            await page.evaluate("""() => { const btn = document.querySelector('div.ui-dialog-buttonpane button'); if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); } }""")
            await page.wait_for_timeout(500)
    except:
        pass
    
    # Xử lý CAPTCHA nếu có
    if not await bypass_captcha(page, doc_id=0):
        print("⚠️ Không thể bypass CAPTCHA khi login")
        await context.close()
        return None
    
    await context.storage_state(path=storage_file)
    await context.close()
    return storage_file

async def check_login_required(page):
    """Kiểm tra xem có cần login không"""
    try:
        login_form = await page.query_selector("#usernameTextBox")
        return login_form is not None
    except:
        return False

def _has_valid_doc_info(doc_info):
    """Check if doc_info has valid data (not empty or 'Dữ liệu đang cập nhật')"""
    return any(v for v in doc_info.values() if v and v != "Dữ liệu đang cập nhật")

async def crawl_one_with_context(context, item, semaphore, timeout_ms):
    """Crawl một văn bản - reuse context trong batch"""
    async with semaphore:
        stt = item.get("Stt") or item.get("stt") or 0
        url = item.get("Url") or item.get("url") or ""
        ten = item.get("Ten van ban") or item.get("ten_van_ban") or ""
        ngay_cap_nhat = item.get("Ngay cap nhat") or item.get("ngay_cap_nhat") or ""
        
        if not url:
            print(f"\n[{stt}] ✗ Missing URL")
            return {"stt": stt, "error": "Missing URL", "doc_info": {}}
        
        print(f"\n[{stt}/{len(links)}] {ten[:60] if ten else 'No title'}...")
        print(f"  URL: {url}")

        # Thêm độ trễ ngẫu nhiên trước mỗi request
        delay = random.uniform(5.0, 8.0)
        print(f"  ⏱ Delay {delay:.1f}s...")
        await asyncio.sleep(delay)
        
        for attempt in range(3):
            page = None
            try:
                page = await context.new_page()
                if STEALTH_AVAILABLE:
                    await stealth_async(page)
                current_timeout = timeout_ms * (1 + attempt)
                data = await extract_luoc_do_async(url, page, timeout_ms=current_timeout)
                data["stt"] = stt
                data["title"] = ten
                if ngay_cap_nhat:
                    data["ngay_cap_nhat"] = ngay_cap_nhat
                
                total = data.get("tab4_total_relations", 0)
                doc_info = data.get("doc_info", {})
                has_valid_data = _has_valid_doc_info(doc_info)
                
                # Check session chỉ khi data null
                if not has_valid_data:
                    if await check_login_required(page):
                        await page.close()
                        raise Exception("Session expired - login required")
                
                # Close page
                await page.close()
                
                if not has_valid_data and attempt < 2:
                    delay = random.uniform(20, 25)
                    print(f"  ⚠ [{stt}] Data null (keys: {list(doc_info.keys())}), retry {attempt+1}/3 sau {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                
                # Skip nếu vẫn null sau 3 retry
                if not has_valid_data:
                    print(f"  ⚠ [{stt}] Data null sau 3 retry (keys: {list(doc_info.keys())}), skip")
                    return {"stt": stt, "url": url, "error": "No valid data after 3 retries", "doc_info": doc_info}
                
                print(f"  ✓ [{stt}] {total} quan hệ")
                return data
            except Exception as e:
                error_msg = str(e)
                if page:
                    try:
                        await page.close()
                    except:
                        pass
                
                # Log chi tiết hơn cho các loại lỗi
                if "CAPTCHA" in error_msg:
                    print(f"  🔒 [{stt}] CAPTCHA không bypass được")
                elif "Timeout" in error_msg:
                    if attempt < 2:
                        delay = random.uniform(20, 25)
                        print(f"  ⚠ [{stt}] Timeout, retry {attempt+1}/3 sau {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                    print(f"  ⚠ [{stt}] Timeout sau 3 lần thử")
                else:
                    print(f"  ✗ [{stt}] {error_msg[:80]}")
                
                return {"stt": stt, "url": url, "error": error_msg, "doc_info": {}}
            
        return {"stt": stt, "url": url, "error": "Failed after retry", "doc_info": {}}

async def crawl_one(browser, item, semaphore, storage_path, timeout_ms):
    """Crawl một văn bản - tạo context riêng (dùng cho retry khi session lỗi)"""
    async with semaphore:
        stt = item.get("Stt") or item.get("stt") or 0
        url = item.get("Url") or item.get("url") or ""
        ten = item.get("Ten van ban") or item.get("ten_van_ban") or ""
        ngay_cap_nhat = item.get("Ngay cap nhat") or item.get("ngay_cap_nhat") or ""
        
        if not url:
            return {"stt": stt, "error": "Missing URL", "doc_info": {}}
        
        print(f"[{stt}/{len(links)}] {ten[:60] if ten else 'No title'}... (RETRY)")
        
        for attempt in range(3):
            context = None
            page = None
            try:
                # Dùng storage_state ở đây vì chúng ta vừa login lại
                context = await browser.new_context(storage_state=str(storage_path))
                page = await context.new_page()
                if STEALTH_AVAILABLE:
                    await stealth_async(page)
                
                current_timeout = timeout_ms * (1 + attempt)
                
                data = await extract_luoc_do_async(url, page, timeout_ms=current_timeout)
                data["stt"] = stt
                data["title"] = ten
                if ngay_cap_nhat:
                    data["ngay_cap_nhat"] = ngay_cap_nhat
                
                await page.close()
                await context.close()
                
                total = data.get("tab4_total_relations", 0)
                doc_info = data.get("doc_info", {})
                has_valid_data = _has_valid_doc_info(doc_info)
                
                if not has_valid_data and attempt < 2:
                    delay = random.uniform(20, 25)
                    print(f"  ⚠ [{stt}] Data null, retry {attempt+1}/3 sau {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                
                # Skip nếu vẫn null sau 3 retry
                if not has_valid_data:
                    print(f"  ⚠ [{stt}] Data null sau 3 retry, skip")
                    return {"stt": stt, "url": url, "error": "No valid data after 3 retries", "doc_info": {}}
                
                print(f"  ✓ [{stt}] {total} quan hệ")
                return data
            except Exception as e:
                error_msg = str(e)
                if page:
                    try: await page.close()
                    except: pass
                if context:
                    try: await context.close()
                    except: pass
                
                if "Timeout" in error_msg and attempt < 2:
                    delay = random.uniform(20, 25)
                    print(f"  ⚠ [{stt}] Timeout, retry {attempt+1}/3 sau {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                
                print(f"  ✗ [{stt}] {error_msg[:80]}")
                return {"stt": stt, "url": url, "error": error_msg, "doc_info": {}}
        
        return {"stt": stt, "url": url, "error": "Failed after retry", "doc_info": {}}

async def main():
    global SAVE_PER_BATCH
    
    # Start single session for entire crawl
    global_session_id = None
    if SAVE_PER_BATCH and os.getenv('SUPABASE_URL'):
        try:
            from tvpl_crawler.utils.import_supabase_v2 import start_session
            global_session_id = start_session()
            print(f"✓ Started crawl session #{global_session_id}\n")
        except Exception as e:
            print(f"⚠ Could not connect to Supabase: {str(e)[:100]}")
            print("⚠ Will save to JSON only (no DB)\n")
            SAVE_PER_BATCH = False
    
    try:
        return await _run_crawl(global_session_id)
    except KeyboardInterrupt:
        if global_session_id:
            try:
                _fail_session(global_session_id, "Cancelled by user")
            except:
                pass
        raise
    except Exception as e:
        if global_session_id:
            try:
                _fail_session(global_session_id, str(e))
            except:
                pass
        raise

def _fail_session(session_id, error_msg):
    try:
        from tvpl_crawler.utils.import_supabase_v2 import supabase
        from datetime import datetime
        supabase.table('crawl_sessions').update({
            'status': 'FAILED',
            'completed_at': datetime.now().isoformat()
        }).eq('session_id', session_id).execute()
        print(f"\n✗ Session #{session_id} marked as FAILED: {error_msg[:100]}")
    except Exception as e:
        print(f"\n⚠ Could not update session: {e}")

async def _run_crawl(global_session_id):
    async with async_playwright() as p:
        # Dùng Chrome thật để bypass Cloudflare (tốt hơn Chromium)
        try:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=not HEADED,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu' if not HEADED else '',  # Tắt GPU check khi headless
                    '--window-size=1920,1080'
                ]
            )
        except:
            print(" using Chromium")
            browser = await p.chromium.launch(
                headless=not HEADED,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu' if not HEADED else '',
                    '--window-size=1920,1080'
                ]
            )
        
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        BATCH_SIZE = 10  # Giảm xuống 5 để tránh Cloudflare
        results = []
        total_new = 0
        total_unchanged = 0
        
        # Login 1 lần ở đầu
        storage_path = Path("data/storage_state.json")
        print("🔐 Đang login...")
        if not await relogin(browser, str(storage_path)):
            print("⚠️ Login thất bại")
            await browser.close()
            return []
        print("✓ Login thành công\n")
        
        # Random User-Agent và Viewport
        user_agent = random.choice(USER_AGENTS)
        viewport = {"width": random.randint(1280, 1920), "height": random.randint(720, 1080)}
        
        # Tạo context 1 lần cho toàn bộ crawl
        context = await browser.new_context(
            storage_state=str(storage_path),
            user_agent=user_agent,
            viewport=viewport,
            ignore_https_errors=True,
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        for batch_idx in range(0, len(links), BATCH_SIZE):
            batch = links[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            total_batches = (len(links) - 1) // BATCH_SIZE + 1
            
            print(f"\n{'='*60}")
            print(f"Batch {batch_num}/{total_batches} - {len(batch)} văn bản")
            print(f"{'='*60}")
            
            tasks = [crawl_one_with_context(context, item, semaphore, TIMEOUT_MS) for item in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Lưu batch vào Supabase ngay (nếu có flag)
            if SAVE_PER_BATCH and global_session_id:
                try:
                    from tvpl_crawler.utils.import_supabase_v2 import save_document
                    compact_batch = compact_schema(batch_results)
                    batch_new = 0
                    batch_unchanged = 0
                    for item in compact_batch:
                        if item.get("error"):
                            continue
                        try:
                            if save_document(item, global_session_id):
                                batch_new += 1
                            else:
                                batch_unchanged += 1
                        except Exception as e:
                            print(f"  ✗ Lỗi lưu Supabase: {e}")
                    total_new += batch_new
                    total_unchanged += batch_unchanged
                    print(f"  💾 Đã lưu batch: {batch_new} changed, {batch_unchanged} unchanged")
                except Exception as e:
                    print(f"  ⚠ Không thể lưu batch: {e}")
            
            # Delay giữa các batch
            if batch_idx + BATCH_SIZE < len(links):
                delay = random.uniform(20, 30)
                print(f"\n⏸  Đợi {delay:.1f}s trước batch tiếp theo...")
                await asyncio.sleep(delay)
        
        await context.close()
        
        # Xử lý các văn bản bị lỗi session expired
        failed_items = [(i, r) for i, r in enumerate(results) if "Session expired" in r.get("error", "")]
        if failed_items:
            print(f"\n{'='*60}")
            print(f"⚠️  {len(failed_items)} văn bản lỗi session expired")
            print(f"🔐 Đang login lại...")
            print(f"{'='*60}")
            
            if await relogin(browser, str(storage_path)):
                print("✓ Login lại thành công\n")
                
                # Tạo context mới với session mới
                retry_context = await browser.new_context(
                    storage_state=str(storage_path),
                    user_agent=user_agent,
                    viewport=viewport,
                    ignore_https_errors=True,
                )
                await retry_context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                """)
                
                # Retry từng văn bản bị lỗi
                print(f"🔄 Đang retry {len(failed_items)} văn bản...\n")
                retry_tasks = [crawl_one_with_context(retry_context, links[i], semaphore, TIMEOUT_MS) for i, _ in failed_items]
                retry_results = await asyncio.gather(*retry_tasks)
                
                # Cập nhật kết quả
                for (idx, _), new_result in zip(failed_items, retry_results):
                    results[idx] = new_result
                
                # Lưu retry results vào Supabase nếu cần
                if SAVE_PER_BATCH and global_session_id:
                    try:
                        from tvpl_crawler.utils.import_supabase_v2 import save_document
                        compact_retry = compact_schema(retry_results)
                        retry_new = 0
                        retry_unchanged = 0
                        for item in compact_retry:
                            if item.get("error"):
                                continue
                            try:
                                if save_document(item, global_session_id):
                                    retry_new += 1
                                else:
                                    retry_unchanged += 1
                            except Exception as e:
                                print(f"  ✗ Lỗi lưu retry: {e}")
                        total_new += retry_new
                        total_unchanged += retry_unchanged
                        print(f"  💾 Đã lưu retry: {retry_new} changed, {retry_unchanged} unchanged")
                    except Exception as e:
                        print(f"  ⚠ Không thể lưu retry: {e}")
                
                await retry_context.close()
                print(f"\n✓ Retry xong {len(failed_items)} văn bản")
            else:
                print("✗ Login lại thất bại, bỏ qua retry")
        
        await browser.close()
    
        # Complete session
        if global_session_id:
            try:
                from tvpl_crawler.utils.import_supabase_v2 import complete_session
                complete_session(global_session_id, len(results), total_new, total_unchanged)
                print(f"\n✓ Completed session #{global_session_id}: {total_new} changed, {total_unchanged} unchanged")
            except Exception as e:
                print(f"\n⚠ Could not complete session: {str(e)[:100]}")
        
        return results

# Chạy crawler
results = asyncio.run(main())

# Lưu JSON trước (backup nếu DB fail)
compact_results = compact_schema(results)
try:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(compact_results, f, ensure_ascii=False, indent=2)
except (IOError, OSError, PermissionError) as e:
    print(f"✗ Lỗi lưu JSON ({type(e).__name__}): {e}")
    backup_file = output_file.parent / f"{output_file.stem}_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(compact_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu backup: {backup_file}")
except Exception as e:
    print(f"✗ Lỗi không xác định ({type(e).__name__}): {e}")
    backup_file = output_file.parent / f"{output_file.stem}_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(compact_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu backup: {backup_file}")

# Note: Database saving is handled by --save-per-batch flag (saves to Supabase per batch)
# Final JSON is kept as backup

print(f"\n{'='*60}")
print(f"Crawl xong {len(results)}/{len(links)} văn bản")
print(f"Kết quả: {output_file}")
print(f"{'='*60}")
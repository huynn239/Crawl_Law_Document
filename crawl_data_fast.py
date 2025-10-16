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
from compact_schema import compact_schema
from tvpl_crawler.db import TVPLDatabase
from tvpl_crawler.playwright_extract_async import extract_luoc_do_async
from tvpl_crawler.captcha_solver import bypass_captcha

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
    print("Usage: python crawl_data_fast.py <input_file> [output_file] [concurrency] [timeout_ms] [--reuse-session] [--headed]")
    print("Example: python crawl_data_fast.py data/links.json data/result.json 2 30000")
    print("         python crawl_data_fast.py data/links.json data/result.json 2 30000 --reuse-session")
    print("         python crawl_data_fast.py data/links.json data/result.json 2 30000 --headed")
    print("Default: concurrency=2, timeout=30000ms (30s)")
    print("--reuse-session: Dùng session có sẵn (không login lại mỗi batch)")
    print("--headed: Hiển thị browser (debug)")
    sys.exit(1)

# Parse arguments
REUSE_SESSION = "--reuse-session" in sys.argv
HEADED = "--headed" in sys.argv
args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

input_file = Path(args[0])
output_file = Path(args[1]) if len(args) >= 2 else input_file.parent / f"{input_file.stem}_Result.json"
CONCURRENCY = int(args[2]) if len(args) >= 3 else 2
TIMEOUT_MS = int(args[3]) if len(args) >= 4 else 30000

links = json.loads(input_file.read_text(encoding="utf-8"))
mode = "REUSE session" if REUSE_SESSION else "LOGIN mỗi batch"
print(f"Crawl {len(links)} văn bản (concurrency={CONCURRENCY}, timeout={TIMEOUT_MS//1000}s, mode={mode})\n")

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
            page.set_default_timeout(60000)  # 60s timeout
            await page.goto("https://thuvienphapluat.vn/", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
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

async def crawl_one_with_context(context, item, semaphore, timeout_ms):
    """Crawl một văn bản - reuse context trong batch"""
    async with semaphore:
        stt = item["Stt"]
        url = item["Url"]
        ten = item["Ten van ban"]
        ngay_cap_nhat = item.get("Ngay cap nhat")
        
        print(f"\n[{stt}/{len(links)}] {ten[:60]}...")
        print(f"  URL: {url}")

        # Thêm độ trễ ngẫu nhiên trước mỗi request (giảm delay để session không hết hạn)
        delay = random.uniform(2.0, 4.0)
        print(f"  ⏱ Delay {delay:.1f}s...")
        await asyncio.sleep(delay)
        
        for attempt in range(2):
            page = None
            try:
                page = await context.new_page()
                current_timeout = timeout_ms * (2 if attempt > 0 else 1)
                data = await extract_luoc_do_async(url, page, timeout_ms=current_timeout)
                data["stt"] = stt
                if ngay_cap_nhat:
                    data["ngay_cap_nhat"] = ngay_cap_nhat
                
                if await check_login_required(page):
                    await page.close()
                    raise Exception("Session expired - login required")
                
                total = data.get("tab4_total_relations", 0)
                doc_info = data.get("doc_info", {})
                has_valid_data = any(v for v in doc_info.values() if v and v != "Dữ liệu đang cập nhật")
                
                await page.close()
                
                if not has_valid_data and attempt < 1:
                    print(f"  ⚠ [{stt}] Data null, retry...")
                    await asyncio.sleep(2)
                    continue
                
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
                    if attempt < 1:
                        print(f"  ⚠ [{stt}] Timeout, retry...")
                        await asyncio.sleep(2)
                        continue
                    print(f"  ⚠ [{stt}] Timeout sau {attempt+1} lần thử")
                else:
                    print(f"  ✗ [{stt}] {error_msg[:80]}")
                
                return {"stt": stt, "url": url, "error": error_msg, "doc_info": {}}
            
        return {"stt": stt, "url": url, "error": "Failed after retry", "doc_info": {}}

async def crawl_one(browser, item, semaphore, storage_path, timeout_ms):
    """Crawl một văn bản - tạo context riêng (dùng cho retry khi session lỗi)"""
    async with semaphore:
        stt = item["Stt"]
        url = item["Url"]
        ten = item["Ten van ban"]
        ngay_cap_nhat = item.get("Ngay cap nhat")
        
        print(f"[{stt}/{len(links)}] {ten[:60]}... (RETRY)")
        
        for attempt in range(2):
            context = None
            page = None
            try:
                # Dùng storage_state ở đây vì chúng ta vừa login lại
                context = await browser.new_context(storage_state=str(storage_path))
                page = await context.new_page()
                
                current_timeout = timeout_ms * (2 if attempt > 0 else 1)
                
                data = await extract_luoc_do_async(url, page, timeout_ms=current_timeout)
                data["stt"] = stt
                if ngay_cap_nhat:
                    data["ngay_cap_nhat"] = ngay_cap_nhat
                
                if await check_login_required(page):
                    await page.close()
                    await context.close()
                    raise Exception("Session expired - login required")
                
                total = data.get("tab4_total_relations", 0)
                doc_info = data.get("doc_info", {})
                has_valid_data = any(v for v in doc_info.values() if v and v != "Dữ liệu đang cập nhật")
                
                await page.close()
                await context.close()
                
                if not has_valid_data and attempt < 1:
                    print(f"  ⚠ [{stt}] Data null, retry với timeout {current_timeout*2}ms...")
                    await asyncio.sleep(2)
                    continue
                
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
                
                if "Timeout" in error_msg and attempt < 1:
                    print(f"  ⚠ [{stt}] Timeout, retry...")
                    await asyncio.sleep(2)
                    continue
                
                print(f"  ✗ [{stt}] {error_msg[:80]}")
                return {"stt": stt, "url": url, "error": error_msg, "doc_info": {}}
        
        return {"stt": stt, "url": url, "error": "Failed after retry", "doc_info": {}}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not HEADED)
        
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        BATCH_SIZE = 15  # Tăng từ 10 lên 15 để giảm số lần login
        results = []
        
        for batch_idx in range(0, len(links), BATCH_SIZE):
            batch = links[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            total_batches = (len(links) - 1) // BATCH_SIZE + 1
            
            print(f"\n{'='*60}")
            print(f"Batch {batch_num}/{total_batches} - {len(batch)} văn bản")
            print(f"{'='*60}")
            
            # Random User-Agent và Viewport
            user_agent = random.choice(USER_AGENTS)
            viewport = {"width": random.randint(1280, 1920), "height": random.randint(720, 1080)}
            
            if REUSE_SESSION:
                # Dùng session có sẵn
                storage_path = Path("data/storage_state.json")
                if not storage_path.exists():
                    print("⚠️  Chưa có session. Đang login...")
                    result = await relogin(browser, str(storage_path))
                    if not result:
                        print("⚠️ Login thất bại, bỏ qua batch này")
                        continue
                
                print(f"♻️  Dùng session có sẵn với UA: ...{user_agent[-30:]}")
                context = await browser.new_context(
                    storage_state=str(storage_path),
                    user_agent=user_agent,
                    viewport=viewport
                )
            else:
                # Login mới cho batch này với session riêng
                batch_storage = f"data/batch_{batch_num}_storage.json"
                print(f"🔐 Login mới với UA: ...{user_agent[-30:]}")
                result = await relogin(browser, batch_storage, user_agent, viewport)
                
                if not result:
                    print("⚠️ Login thất bại (CAPTCHA?), bỏ qua batch này")
                    continue
                
                context = await browser.new_context(
                    storage_state=batch_storage,
                    user_agent=user_agent,
                    viewport=viewport
                )
            
            tasks = [crawl_one_with_context(context, item, semaphore, TIMEOUT_MS) for item in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            await context.close()
            
            # Xóa session cũ (chỉ khi login mới)
            if not REUSE_SESSION:
                try:
                    Path(batch_storage).unlink()
                except:
                    pass
            
            if batch_idx + BATCH_SIZE < len(links):
                delay = random.uniform(10, 20)
                print(f"\n⏸  Đợi {delay:.1f}s trước batch tiếp theo...")
                await asyncio.sleep(delay)
        
        # Xử lý các văn bản bị lỗi session
        failed_items = [(i, r) for i, r in enumerate(results) if "Session expired" in r.get("error", "")]
        if failed_items:
            print(f"\n⚠️  {len(failed_items)} văn bản lỗi session. Login lại...")
            retry_storage = "data/retry_storage.json"
            await relogin(browser, retry_storage)
            
            retry_tasks = [crawl_one(browser, links[i], semaphore, Path(retry_storage), TIMEOUT_MS) for i, _ in failed_items]
            retry_results = await asyncio.gather(*retry_tasks)
            
            for (idx, _), new_result in zip(failed_items, retry_results):
                results[idx] = new_result
            
            try:
                Path(retry_storage).unlink()
            except:
                pass
            
            print(f"✓ Retry xong {len(failed_items)} văn bản")
            
        await browser.close()
    
    return results

# Chạy crawler
results = asyncio.run(main())

# Lưu JSON trước (backup nếu DB fail)
compact_results = compact_schema(results)
try:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(compact_results, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"✗ Lỗi lưu JSON: {e}")
    backup_file = output_file.parent / f"{output_file.stem}_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(compact_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu backup: {backup_file}")

# Lưu vào database
db = None
session_id = None
try:
    from tvpl_crawler.db import HAS_PSYCOPG2
    if not HAS_PSYCOPG2:
        print("\n⚠ psycopg2 chưa cài, bỏ qua lưu database")
        print("ℹ Dữ liệu đã được lưu trong file JSON")
    else:
        db = TVPLDatabase(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tvpl_crawl"),
        user=os.getenv("DB_USER", "tvpl_user"),
        password=os.getenv("DB_PASSWORD", "")
    )
    
    db.connect()
    print("\nĐang lưu vào database...")
    
    session_id = db.start_crawl_session()
    print(f"✓ Session #{session_id}")
    
    new_versions = 0
    unchanged = 0
    errors = 0
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
            errors += 1
            print(f"  Lỗi lưu {item.get('url', '')}: {e}")
    
    if errors > 0:
        db.fail_crawl_session(session_id, len(compact_results), new_versions, unchanged, errors)
        print(f"✗ Hoàn tất với lỗi: {new_versions} thay đổi, {unchanged} không đổi, {errors} lỗi")
    else:
        db.complete_crawl_session(session_id, len(compact_results), new_versions, unchanged)
        print(f"✓ Hoàn tất: {new_versions} thay đổi, {unchanged} không đổi")
    
        db.close()
except Exception as e:
    print(f"✗ Lỗi database: {e}")
    print("ℹ Dữ liệu đã được lưu trong file JSON")
    if db and session_id:
        try:
            db.fail_crawl_session(session_id, 0, 0, 0, 1)
            db.close()
        except:
            pass

print(f"\n{'='*60}")
print(f"Crawl xong {len(results)}/{len(links)} văn bản")
print(f"Kết quả: {output_file}")
print(f"{'='*60}")